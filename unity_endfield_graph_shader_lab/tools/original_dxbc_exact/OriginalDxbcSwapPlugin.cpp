#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <bcrypt.h>
#include <d3d11.h>
#include <d3dcompiler.h>

#include <atomic>
#include <cmath>
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
#include "M13CapturePayload.generated.h"
#include "M14CapturePayload.generated.h"
#include "M18PeakCapturePayload.generated.h"
#include "M20PeakCapturePayload.generated.h"
#include "M21PeakCapturePayload.generated.h"
#include "M28PeakCapturePayload.generated.h"
#include "M27CapturePayload.generated.h"
#include "M27TemporalCapturePayload.generated.h"
#include "M29CapturePayload.generated.h"
#include "M30CapturePayload.generated.h"
#include "M31PeakCapturePayload.generated.h"
#include "M31FixedStateContract.h"
#include "OpeningStripCapturePayload.generated.h"
#include "VFXBaseV2PeakCohortPayload.generated.h"
#include "M27SubstitutionRegistry.h"

#if __has_include("EndminfUberCapturePayload.generated.h")
#include "EndminfUberCapturePayload.generated.h"
#else
#include "EndminfUberCapturePayload.fallback.h"
#endif

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
ID3D11Buffer* g_m14VertexBuffers[g_EndfieldM14PacketCount] = {};
ID3D11Buffer* g_m14DefaultVertexBuffer = nullptr;
ID3D11Buffer* g_m14IndexBuffers[g_EndfieldM14PacketCount] = {};
ID3D11Buffer* g_m14VertexConstantBuffers[g_EndfieldM14PacketCount][5] = {};
ID3D11Buffer* g_m14PixelConstantBuffers[g_EndfieldM14PacketCount][4] = {};
ID3D11Buffer* g_m14SkinBuffer = nullptr;
ID3D11ShaderResourceView* g_m14SkinView = nullptr;
ID3D11SamplerState* g_m14Samplers[2] = {};
ID3D11BlendState* g_m14BlendState = nullptr;
ID3D11DepthStencilState* g_m14DepthState = nullptr;
ID3D11RasterizerState* g_m14RasterizerState = nullptr;
std::atomic<std::uintptr_t> g_m14DepthTexture{0};
std::atomic<std::uintptr_t> g_m14MainTexture{0};
std::atomic<std::uint32_t> g_m14PacketIndex{0};
std::atomic<std::uint64_t> g_m14OutputDimensions{0};
std::atomic<std::uint32_t> g_m14ScreenSizePatched{0};
std::uint32_t g_m14ResourceWidth = 0;
std::uint32_t g_m14ResourceHeight = 0;
std::atomic<std::uint32_t> g_m14DrawCount{0};
std::atomic<std::uint32_t> g_m14FailureCount{0};
std::atomic<HRESULT> g_m14LastResult{S_OK};

ID3D11Buffer* g_m31PeakVertexBuffers[g_EndfieldM31PeakDrawPayloadCount] = {};
ID3D11Buffer* g_m31PeakSecondaryBuffers[g_EndfieldM31PeakDrawPayloadCount] = {};
ID3D11Buffer* g_m31PeakIndexBuffers[g_EndfieldM31PeakDrawPayloadCount] = {};
ID3D11Buffer* g_m31PeakVertexConstantBuffers[g_EndfieldM31PeakDrawPayloadCount][5] = {};
ID3D11Buffer* g_m31PeakPixelConstantBuffers[g_EndfieldM31PeakDrawPayloadCount][4] = {};
ID3D11Texture2D* g_m31PeakMainTexture = nullptr;
ID3D11ShaderResourceView* g_m31PeakMainView = nullptr;
ID3D11SamplerState* g_m31PeakSamplers[2] = {};
ID3D11BlendState* g_m31PeakBlendState = nullptr;
ID3D11DepthStencilState* g_m31PeakDepthState = nullptr;
ID3D11RasterizerState* g_m31PeakRasterizerState = nullptr;
std::atomic<std::uintptr_t> g_m31PeakDepthTexture{0};
std::atomic<std::uint32_t> g_m31PeakTemporalPacketIndex{
    (std::numeric_limits<std::uint32_t>::max)()};
std::atomic<std::uint32_t> g_m31PeakDrawCount{0};
std::atomic<std::uint32_t> g_m31PeakFailureCount{0};
std::atomic<HRESULT> g_m31PeakLastResult{S_OK};

ID3D11VertexShader* g_m21PeakVertexShader = nullptr;
ID3D11PixelShader* g_m21PeakPixelShader = nullptr;
ID3D11InputLayout* g_m21PeakInputLayout = nullptr;
ID3D11Buffer* g_m21PeakVertexBuffer = nullptr;
ID3D11Buffer* g_m21PeakSecondaryBuffer = nullptr;
ID3D11Buffer* g_m21PeakIndexBuffer = nullptr;
ID3D11Buffer* g_m21PeakVertexConstantBuffers[5] = {};
ID3D11Buffer* g_m21PeakPixelConstantBuffers[5] = {};
ID3D11Texture2D* g_m21PeakWhiteTexture = nullptr;
ID3D11ShaderResourceView* g_m21PeakWhiteView = nullptr;
ID3D11SamplerState* g_m21PeakSampler = nullptr;
ID3D11BlendState* g_m21PeakBlendState = nullptr;
ID3D11DepthStencilState* g_m21PeakDepthState = nullptr;
ID3D11RasterizerState* g_m21PeakRasterizerState = nullptr;
std::atomic<std::uint32_t> g_m21PeakDrawCount{0};
std::atomic<std::uint32_t> g_m21PeakFailureCount{0};
std::atomic<HRESULT> g_m21PeakLastResult{S_OK};
std::atomic<std::uint64_t> g_m21PeakOutputDimensions{0};
std::atomic<std::uint32_t> g_m21PeakScreenSizePatched{0};
std::uint32_t g_m21PeakResourceWidth = 0;
std::uint32_t g_m21PeakResourceHeight = 0;

ID3D11VertexShader* g_m20PeakVertexShader = nullptr;
ID3D11PixelShader* g_m20PeakPixelShader = nullptr;
ID3D11InputLayout* g_m20PeakInputLayout = nullptr;
ID3D11Buffer* g_m20PeakVertexBuffer = nullptr;
ID3D11Buffer* g_m20PeakSecondaryBuffer = nullptr;
ID3D11Buffer* g_m20PeakIndexBuffer = nullptr;
ID3D11Buffer* g_m20PeakVertexResource = nullptr;
ID3D11ShaderResourceView* g_m20PeakVertexView = nullptr;
ID3D11Buffer* g_m20PeakVertexConstantBuffers[5] = {};
ID3D11Buffer* g_m20PeakPixelConstantBuffers[4] = {};
ID3D11Texture2D* g_m20PeakAtlasTexture = nullptr;
ID3D11ShaderResourceView* g_m20PeakAtlasView = nullptr;
ID3D11SamplerState* g_m20PeakSamplers[2] = {};
ID3D11BlendState* g_m20PeakBlendState = nullptr;
ID3D11DepthStencilState* g_m20PeakDepthState = nullptr;
ID3D11RasterizerState* g_m20PeakRasterizerState = nullptr;
std::atomic<std::uintptr_t> g_m20PeakDepthTexture{0};
std::atomic<std::uint64_t> g_m20PeakOutputDimensions{0};
std::atomic<std::uint32_t> g_m20PeakScreenSizePatched{0};
std::uint32_t g_m20PeakResourceWidth = 0;
std::uint32_t g_m20PeakResourceHeight = 0;
std::atomic<std::uint32_t> g_m20PeakDrawCount{0};
std::atomic<std::uint32_t> g_m20PeakFailureCount{0};
std::atomic<HRESULT> g_m20PeakLastResult{S_OK};

ID3D11VertexShader* g_m18PeakVertexShader = nullptr;
ID3D11PixelShader* g_m18PeakPixelShader = nullptr;
ID3D11InputLayout* g_m18PeakInputLayout = nullptr;
ID3D11Buffer* g_m18PeakVertexBuffer = nullptr;
ID3D11Buffer* g_m18PeakSecondaryBuffer = nullptr;
ID3D11Buffer* g_m18PeakIndexBuffer = nullptr;
ID3D11Buffer* g_m18PeakVertexConstantBuffers[5] = {};
ID3D11Buffer* g_m18PeakPixelConstantBuffers[4] = {};
ID3D11SamplerState* g_m18PeakSamplers[5] = {};
ID3D11BlendState* g_m18PeakBlendState = nullptr;
ID3D11DepthStencilState* g_m18PeakDepthState = nullptr;
ID3D11RasterizerState* g_m18PeakRasterizerState = nullptr;
std::atomic<std::uintptr_t> g_m18PeakTextures[5] = {};
std::atomic<std::uint64_t> g_m18PeakOutputDimensions{0};
std::atomic<std::uint32_t> g_m18PeakScreenSizePatched{0};
std::uint32_t g_m18PeakResourceWidth = 0;
std::uint32_t g_m18PeakResourceHeight = 0;
std::atomic<std::uint32_t> g_m18PeakDrawCount{0};
std::atomic<std::uint32_t> g_m18PeakFailureCount{0};
std::atomic<HRESULT> g_m18PeakLastResult{S_OK};

ID3D11VertexShader* g_m28PeakVertexShader = nullptr;
ID3D11PixelShader* g_m28PeakPixelShader = nullptr;
ID3D11InputLayout* g_m28PeakInputLayout = nullptr;
ID3D11Buffer* g_m28PeakVertexBuffer = nullptr;
ID3D11Buffer* g_m28PeakSecondaryBuffer = nullptr;
ID3D11Buffer* g_m28PeakIndexBuffer = nullptr;
ID3D11Buffer* g_m28PeakVertexConstantBuffers[5] = {};
ID3D11Buffer* g_m28PeakPixelConstantBuffers[4] = {};
ID3D11SamplerState* g_m28PeakSamplers[3] = {};
ID3D11BlendState* g_m28PeakBlendState = nullptr;
ID3D11DepthStencilState* g_m28PeakDepthState = nullptr;
ID3D11RasterizerState* g_m28PeakRasterizerState = nullptr;
std::atomic<std::uintptr_t> g_m28PeakTextures[3] = {};
std::atomic<std::uint64_t> g_m28PeakOutputDimensions{0};
std::atomic<std::uint32_t> g_m28PeakScreenSizePatched{0};
std::uint32_t g_m28PeakResourceWidth = 0;
std::uint32_t g_m28PeakResourceHeight = 0;
std::atomic<std::uint32_t> g_m28PeakDrawCount{0};
std::atomic<std::uint32_t> g_m28PeakFailureCount{0};
std::atomic<HRESULT> g_m28PeakLastResult{S_OK};

ID3D11Buffer* g_vfxPeakVertexBuffers[g_EndfieldVFXPeakDrawCount] = {};
ID3D11Buffer* g_vfxPeakSecondaryBuffer = nullptr;
ID3D11Buffer* g_vfxPeakIndexBuffers[g_EndfieldVFXPeakDrawCount] = {};
ID3D11Buffer* g_vfxPeakVertexConstantBuffers[g_EndfieldVFXPeakDrawCount][5] = {};
ID3D11Buffer* g_vfxPeakPixelConstantBuffers[g_EndfieldVFXPeakDrawCount][4] = {};
ID3D11Texture2D* g_vfxPeakTextures[g_EndfieldVFXPeakTextureCount] = {};
ID3D11ShaderResourceView* g_vfxPeakTextureViews[g_EndfieldVFXPeakTextureCount] = {};
ID3D11SamplerState* g_vfxPeakSamplers[2] = {};
ID3D11BlendState* g_vfxPeakBlendState = nullptr;
ID3D11DepthStencilState* g_vfxPeakDepthState = nullptr;
ID3D11RasterizerState* g_vfxPeakRasterizerState = nullptr;
std::atomic<std::uintptr_t> g_vfxPeakDepthTexture{0};
std::atomic<std::uint32_t> g_vfxPeakDrawCount{0};
std::atomic<std::uint32_t> g_vfxPeakFailureCount{0};
std::atomic<HRESULT> g_vfxPeakLastResult{S_OK};

ID3D11Buffer* g_m30VertexBuffers[g_EndfieldM30PacketCount] = {};
ID3D11Buffer* g_m30SecondaryBuffers[g_EndfieldM30PacketCount] = {};
ID3D11Buffer* g_m30IndexBuffers[g_EndfieldM30PacketCount] = {};
ID3D11Buffer* g_m30VertexConstantBuffers[g_EndfieldM30PacketCount][5] = {};
ID3D11Buffer* g_m30PixelConstantBuffers[g_EndfieldM30PacketCount][4] = {};
ID3D11Texture2D* g_m30MainTexture = nullptr;
ID3D11ShaderResourceView* g_m30MainView = nullptr;
std::atomic<std::uintptr_t> g_m30DepthTexture{0};
std::atomic<std::uint32_t> g_m30PacketIndex{0};
std::atomic<std::uint32_t> g_m30DrawCount{0};
std::atomic<std::uint32_t> g_m30FailureCount{0};
std::atomic<HRESULT> g_m30LastResult{S_OK};

constexpr std::size_t kM29VSConstantBufferCount =
    sizeof(g_EndfieldM29VSDeclaredFloat4Counts) /
    sizeof(g_EndfieldM29VSDeclaredFloat4Counts[0]);
constexpr std::size_t kM29PSConstantBufferCount =
    sizeof(g_EndfieldM29PSDeclaredFloat4Counts) /
    sizeof(g_EndfieldM29PSDeclaredFloat4Counts[0]);
ID3D11VertexShader* g_m29RuntimeVertexShader = nullptr;
ID3D11PixelShader* g_m29RuntimePixelShader = nullptr;
ID3D11InputLayout* g_m29InputLayouts[2] = {};
ID3D11Buffer* g_m29VertexBuffers[g_EndfieldM29PacketCount] = {};
ID3D11Buffer* g_m29SecondaryBuffers[g_EndfieldM29PacketCount] = {};
ID3D11Buffer* g_m29IndexBuffers[g_EndfieldM29PacketCount] = {};
ID3D11Buffer* g_m29VertexConstantBuffers
    [g_EndfieldM29PacketCount][kM29VSConstantBufferCount] = {};
ID3D11Buffer* g_m29PixelConstantBuffers
    [g_EndfieldM29PacketCount][kM29PSConstantBufferCount] = {};
ID3D11Buffer* g_m29SkinBuffer = nullptr;
ID3D11ShaderResourceView* g_m29SkinView = nullptr;
ID3D11Texture2D* g_m29Textures[2] = {};
ID3D11ShaderResourceView* g_m29TextureViews[2] = {};
ID3D11SamplerState* g_m29Samplers[3] = {};
ID3D11BlendState* g_m29BlendState = nullptr;
ID3D11DepthStencilState* g_m29DepthState = nullptr;
ID3D11RasterizerState* g_m29RasterizerState = nullptr;
std::atomic<std::uintptr_t> g_m29DepthTexture{0};
std::atomic<std::uint32_t> g_m29PacketIndex{0};
std::atomic<std::uint32_t> g_m29DrawCount{0};
std::atomic<std::uint32_t> g_m29FailureCount{0};
std::atomic<HRESULT> g_m29LastResult{S_OK};

ID3D11VertexShader* g_m13RuntimeVertexShader = nullptr;
ID3D11PixelShader* g_m13RuntimePixelShader = nullptr;
ID3D11InputLayout* g_m13InputLayout = nullptr;
ID3D11Buffer* g_m13VertexBuffers[g_EndfieldM13PacketCount] = {};
ID3D11Buffer* g_m13DefaultVertexBuffer = nullptr;
ID3D11Buffer* g_m13IndexBuffer = nullptr;
ID3D11Buffer* g_m13VertexConstantBuffers[g_EndfieldM13PacketCount][5] = {};
ID3D11Buffer* g_m13PixelConstantBuffers[g_EndfieldM13PacketCount][4] = {};
std::atomic<std::uint64_t> g_m13OutputDimensions{0};
std::atomic<std::uint32_t> g_m13ScreenSizePatched{0};
std::uint32_t g_m13ResourceWidth = 0;
std::uint32_t g_m13ResourceHeight = 0;
ID3D11Buffer* g_m13SkinBuffer = nullptr;
ID3D11ShaderResourceView* g_m13SkinView = nullptr;
ID3D11Texture2D* g_m13Textures[5] = {};
ID3D11ShaderResourceView* g_m13TextureViews[5] = {};
ID3D11SamplerState* g_m13Samplers[5] = {};
ID3D11BlendState* g_m13BlendState = nullptr;
ID3D11DepthStencilState* g_m13DepthState = nullptr;
ID3D11RasterizerState* g_m13RasterizerState = nullptr;
std::atomic<std::uint32_t> g_m13DrawCount{0};
std::atomic<std::uint32_t> g_m13FailureCount{0};
std::atomic<HRESULT> g_m13LastResult{S_OK};
std::atomic<std::uint32_t> g_m13PacketIndex{0};

ID3D11VertexShader* g_openingStripVertexShader = nullptr;
ID3D11PixelShader* g_openingStripPixelShader = nullptr;
ID3D11InputLayout* g_openingStripInputLayout = nullptr;
ID3D11Buffer* g_openingStripVertexBuffers[g_EndfieldOpeningStripPacketCount] = {};
ID3D11Buffer* g_openingStripIndexBuffers[g_EndfieldOpeningStripPacketCount] = {};
ID3D11Buffer* g_openingStripDefaultVertexBuffer = nullptr;
ID3D11Buffer* g_openingStripVertexConstantBuffers[g_EndfieldOpeningStripPacketCount][5] = {};
ID3D11Buffer* g_openingStripPixelConstantBuffers[g_EndfieldOpeningStripPacketCount][4] = {};
ID3D11Buffer* g_openingStripSkinBuffer = nullptr;
ID3D11ShaderResourceView* g_openingStripSkinView = nullptr;
ID3D11Texture2D* g_openingStripMaskTexture = nullptr;
ID3D11ShaderResourceView* g_openingStripMaskView = nullptr;
ID3D11SamplerState* g_openingStripSamplers[2] = {};
ID3D11BlendState* g_openingStripBlendState = nullptr;
ID3D11DepthStencilState* g_openingStripDepthState = nullptr;
ID3D11RasterizerState* g_openingStripRasterizerState = nullptr;
std::atomic<std::uintptr_t> g_openingStripSceneColor{0};
std::atomic<std::uint64_t> g_openingStripOutputDimensions{0};
std::atomic<std::uint32_t> g_openingStripScreenSizePatched{0};
std::atomic<std::uint32_t> g_openingStripPacketIndex{0};
std::atomic<std::uint32_t> g_openingStripDrawCount{0};
std::atomic<std::uint32_t> g_openingStripFailureCount{0};
std::atomic<HRESULT> g_openingStripLastResult{S_OK};
std::uint32_t g_openingStripResourceWidth = 0;
std::uint32_t g_openingStripResourceHeight = 0;

ID3D11VertexShader* g_m27DrawVertexShader = nullptr;
ID3D11PixelShader* g_m27DrawPixelShader = nullptr;
constexpr std::uint32_t kM27MaximumDrawsPerFrame =
    g_EndfieldM27TemporalMaximumDrawsPerFrame;
ID3D11InputLayout* g_m27DrawInputLayouts[2] = {};
ID3D11Buffer* g_m27DrawVertexBuffers
    [g_EndfieldM27TemporalFrameCount][kM27MaximumDrawsPerFrame] = {};
ID3D11Buffer* g_m27DrawDefaultVertexBuffer = nullptr;
ID3D11Buffer* g_m27DrawIndexBuffers
    [g_EndfieldM27TemporalFrameCount][kM27MaximumDrawsPerFrame] = {};
ID3D11Buffer* g_m27DrawVertexConstantBuffers
    [g_EndfieldM27TemporalFrameCount][kM27MaximumDrawsPerFrame][3] = {};
ID3D11Buffer* g_m27DrawPixelConstantBuffers
    [g_EndfieldM27TemporalFrameCount][kM27MaximumDrawsPerFrame][5] = {};
ID3D11Buffer* g_m27DrawSkinBuffer = nullptr;
ID3D11ShaderResourceView* g_m27DrawSkinView = nullptr;
ID3D11Texture2D* g_m27DrawTextures[6] = {};
ID3D11ShaderResourceView* g_m27DrawTextureViews[6] = {};
ID3D11SamplerState* g_m27DrawSampler = nullptr;
ID3D11BlendState* g_m27DrawBlendState = nullptr;
ID3D11DepthStencilState* g_m27DrawDepthState = nullptr;
ID3D11RasterizerState* g_m27DrawRasterizerState = nullptr;
std::atomic<std::uint32_t> g_m27DrawPacketIndex{0};
std::atomic<std::uint32_t> g_m27DrawCount{0};
std::atomic<std::uint32_t> g_m27DrawFailureCount{0};
std::atomic<HRESULT> g_m27DrawLastResult{S_OK};
std::atomic<std::uint32_t> g_m27DrawFailureStage{0};

constexpr std::size_t kEndminfUberPacketCapacity = 64;
constexpr std::uint32_t kEndminfUberMaximumEventId = 0x7fffffffu;
constexpr std::size_t kEndminfUberVsB0Bytes = 1u * 16u;
constexpr std::size_t kEndminfUberPsB0Bytes = 28u * 16u;
constexpr std::size_t kEndminfUberPsB1Bytes = 26u * 16u;
static_assert(g_EndfieldUberVsB0Size == kEndminfUberVsB0Bytes);
static_assert(g_EndfieldUberPsB0Size == kEndminfUberPsB0Bytes);
static_assert(g_EndfieldUberPsB1Size == kEndminfUberPsB1Bytes);
static_assert(g_EndfieldM30PayloadPrepared);
static_assert(g_EndfieldM21PeakPayloadPrepared);
static_assert(g_EndfieldM21PeakVertexStride == 52u);
static_assert(g_EndfieldM21PeakIndexCount == 1110u);
static_assert(g_EndfieldM20PeakPayloadPrepared);
static_assert(g_EndfieldM20PeakVertexStride == 36u);
static_assert(g_EndfieldM20PeakVertexCount == 24u);
static_assert(g_EndfieldM20PeakIndexCount == 36u);
static_assert(g_EndfieldM20PeakAtlasBc7Size == 32768u);
static_assert(g_EndfieldM18PeakPayloadPrepared);
static_assert(g_EndfieldM18PeakVertexStride == 76u);
static_assert(g_EndfieldM18PeakIndexCount == 900u);
static_assert(g_EndfieldM28PeakPayloadPrepared);
static_assert(g_EndfieldM28PeakVertexStride == 60u);
static_assert(g_EndfieldM28PeakVertexCount == 344u);
static_assert(g_EndfieldM28PeakIndexCount == 1764u);
static_assert(g_EndfieldM30DepthContractReady);
static_assert(g_EndfieldM30PacketCount == 6u);
static_assert(g_EndfieldM30TextureT1Size == 65536u);
static_assert(g_EndfieldM30TextureWidth == 256u &&
    g_EndfieldM30TextureHeight == 256u);
static_assert(g_EndfieldM29PayloadPrepared);
static_assert(g_EndfieldM29PacketCount > 0u);
static_assert(kM29VSConstantBufferCount == 5u);
static_assert(kM29PSConstantBufferCount == 4u);
static_assert(g_EndfieldM29TextureT0Size == 65536u);
static_assert(g_EndfieldM29TextureT1Size == 262144u);
static_assert(g_EndfieldM31PeakPayloadPrepared);
static_assert(g_EndfieldM31PeakDepthContractReady);
static_assert(g_EndfieldM31PeakTemporalPacketCount == 9u);
static_assert(g_EndfieldM31PeakDrawPayloadCount == 18u);
static_assert(g_EndfieldM31PeakMaxEventCount == 3u);
static_assert(g_EndfieldM31PeakTemporalPackets[0].scheduleProfile ==
        g_EndfieldM31PeakScheduleQueue3000Interval2 &&
    g_EndfieldM31PeakTemporalPackets[0].chronologyValidated);
static_assert(g_EndfieldM31PeakTemporalPackets[6].scheduleProfile ==
        g_EndfieldM31PeakScheduleQueue3000Interval2 &&
    g_EndfieldM31PeakTemporalPackets[6].chronologyValidated);
static_assert(g_EndfieldM31PeakTemporalPackets[7].drawCount == 3u &&
    g_EndfieldM31PeakTemporalPackets[7].scheduleProfile ==
        g_EndfieldM31PeakScheduleQueue3000ThenPostM18_3 &&
    !g_EndfieldM31PeakTemporalPackets[7].chronologyValidated);
static_assert(g_EndfieldM31PeakTextureT1Size == 65536u);
static_assert(g_EndfieldVFXPeakPayloadPrepared);
static_assert(g_EndfieldVFXPeakDrawCount == 15u);
static_assert(g_EndfieldVFXPeakTextureCount == 5u);

enum class EndminfUberPacketState : std::uint32_t
{
    Empty = 0,
    Ready = 1,
    Consuming = 2,
};

enum class EndminfUberVariant : std::uint32_t
{
    Normal = 0,
    Peak = 1,
};

struct EndminfUberPacket
{
    std::atomic<EndminfUberPacketState> state{EndminfUberPacketState::Empty};
    std::atomic<std::uint32_t> eventId{0};
    EndminfUberVariant variant = EndminfUberVariant::Peak;
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    std::uint8_t vsB0[kEndminfUberVsB0Bytes] = {};
    std::uint8_t psB0[kEndminfUberPsB0Bytes] = {};
    std::uint8_t psB1[kEndminfUberPsB1Bytes] = {};
    ID3D11Texture2D* textures[3] = {};
};

EndminfUberPacket g_endminfUberPackets[kEndminfUberPacketCapacity] = {};
std::mutex g_endminfUberMutex;
ID3D11Texture2D* g_endminfUberConfiguredTextures[3] = {};
std::uint32_t g_endminfUberNextEventId = 1;
ID3D11VertexShader* g_endminfUberVertexShader = nullptr;
ID3D11PixelShader* g_endminfUberNormalPixelShader = nullptr;
ID3D11PixelShader* g_endminfUberPixelShader = nullptr;
ID3D11SamplerState* g_endminfUberSampler = nullptr;
ID3D11BlendState* g_endminfUberBlendState = nullptr;
ID3D11DepthStencilState* g_endminfUberDepthState = nullptr;
ID3D11RasterizerState* g_endminfUberRasterizerState = nullptr;
ID3D11Texture2D* g_endminfUberOutputDepthTexture = nullptr;
ID3D11DepthStencilView* g_endminfUberOutputDepthView = nullptr;
std::atomic<std::uint32_t> g_endminfUberDrawCount{0};
std::atomic<std::uint32_t> g_endminfUberFailureCount{0};
std::atomic<HRESULT> g_endminfUberLastResult{S_OK};
std::atomic<std::uint32_t> g_endminfUberFailureStage{0};

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
    g_m18PeakScreenSizePatched.store(0, std::memory_order_release);
    g_m18PeakResourceWidth = 0;
    g_m18PeakResourceHeight = 0;
    g_m28PeakScreenSizePatched.store(0, std::memory_order_release);
    g_m28PeakResourceWidth = 0;
    g_m28PeakResourceHeight = 0;
    g_m14ScreenSizePatched.store(0, std::memory_order_release);
    g_m14ResourceWidth = 0;
    g_m14ResourceHeight = 0;
    g_m21PeakScreenSizePatched.store(0, std::memory_order_release);
    g_m21PeakResourceWidth = 0;
    g_m21PeakResourceHeight = 0;
    g_m20PeakScreenSizePatched.store(0, std::memory_order_release);
    g_m20PeakResourceWidth = 0;
    g_m20PeakResourceHeight = 0;
    ReleaseM14Object(g_m20PeakRasterizerState);
    ReleaseM14Object(g_m20PeakDepthState);
    ReleaseM14Object(g_m20PeakBlendState);
    for (ID3D11SamplerState*& sampler : g_m20PeakSamplers)
        ReleaseM14Object(sampler);
    ReleaseM14Object(g_m20PeakAtlasView);
    ReleaseM14Object(g_m20PeakAtlasTexture);
    for (ID3D11Buffer*& buffer : g_m20PeakPixelConstantBuffers)
        ReleaseM14Object(buffer);
    for (ID3D11Buffer*& buffer : g_m20PeakVertexConstantBuffers)
        ReleaseM14Object(buffer);
    ReleaseM14Object(g_m20PeakVertexView);
    ReleaseM14Object(g_m20PeakVertexResource);
    ReleaseM14Object(g_m20PeakIndexBuffer);
    ReleaseM14Object(g_m20PeakSecondaryBuffer);
    ReleaseM14Object(g_m20PeakVertexBuffer);
    ReleaseM14Object(g_m20PeakInputLayout);
    ReleaseM14Object(g_m20PeakPixelShader);
    ReleaseM14Object(g_m20PeakVertexShader);
    ReleaseM14Object(g_m28PeakRasterizerState);
    ReleaseM14Object(g_m28PeakDepthState);
    ReleaseM14Object(g_m28PeakBlendState);
    for (ID3D11SamplerState*& sampler : g_m28PeakSamplers)
        ReleaseM14Object(sampler);
    for (ID3D11Buffer*& buffer : g_m28PeakPixelConstantBuffers)
        ReleaseM14Object(buffer);
    for (ID3D11Buffer*& buffer : g_m28PeakVertexConstantBuffers)
        ReleaseM14Object(buffer);
    ReleaseM14Object(g_m28PeakIndexBuffer);
    ReleaseM14Object(g_m28PeakSecondaryBuffer);
    ReleaseM14Object(g_m28PeakVertexBuffer);
    ReleaseM14Object(g_m28PeakInputLayout);
    ReleaseM14Object(g_m28PeakPixelShader);
    ReleaseM14Object(g_m28PeakVertexShader);
    ReleaseM14Object(g_m18PeakRasterizerState);
    ReleaseM14Object(g_m18PeakDepthState);
    ReleaseM14Object(g_m18PeakBlendState);
    for (ID3D11SamplerState*& sampler : g_m18PeakSamplers)
        ReleaseM14Object(sampler);
    for (ID3D11Buffer*& buffer : g_m18PeakPixelConstantBuffers)
        ReleaseM14Object(buffer);
    for (ID3D11Buffer*& buffer : g_m18PeakVertexConstantBuffers)
        ReleaseM14Object(buffer);
    ReleaseM14Object(g_m18PeakIndexBuffer);
    ReleaseM14Object(g_m18PeakSecondaryBuffer);
    ReleaseM14Object(g_m18PeakVertexBuffer);
    ReleaseM14Object(g_m18PeakInputLayout);
    ReleaseM14Object(g_m18PeakPixelShader);
    ReleaseM14Object(g_m18PeakVertexShader);
    ReleaseM14Object(g_m21PeakRasterizerState);
    ReleaseM14Object(g_m21PeakDepthState);
    ReleaseM14Object(g_m21PeakBlendState);
    ReleaseM14Object(g_m21PeakSampler);
    ReleaseM14Object(g_m21PeakWhiteView);
    ReleaseM14Object(g_m21PeakWhiteTexture);
    for (ID3D11Buffer*& buffer : g_m21PeakPixelConstantBuffers)
        ReleaseM14Object(buffer);
    for (ID3D11Buffer*& buffer : g_m21PeakVertexConstantBuffers)
        ReleaseM14Object(buffer);
    ReleaseM14Object(g_m21PeakIndexBuffer);
    ReleaseM14Object(g_m21PeakSecondaryBuffer);
    ReleaseM14Object(g_m21PeakVertexBuffer);
    ReleaseM14Object(g_m21PeakInputLayout);
    ReleaseM14Object(g_m21PeakPixelShader);
    ReleaseM14Object(g_m21PeakVertexShader);
    ReleaseM14Object(g_vfxPeakRasterizerState);
    ReleaseM14Object(g_vfxPeakDepthState);
    ReleaseM14Object(g_vfxPeakBlendState);
    for (ID3D11SamplerState*& sampler : g_vfxPeakSamplers)
        ReleaseM14Object(sampler);
    for (ID3D11ShaderResourceView*& view : g_vfxPeakTextureViews)
        ReleaseM14Object(view);
    for (ID3D11Texture2D*& texture : g_vfxPeakTextures)
        ReleaseM14Object(texture);
    for (std::uint32_t draw = 0; draw < g_EndfieldVFXPeakDrawCount; ++draw)
    {
        for (ID3D11Buffer*& buffer : g_vfxPeakPixelConstantBuffers[draw])
            ReleaseM14Object(buffer);
        for (ID3D11Buffer*& buffer : g_vfxPeakVertexConstantBuffers[draw])
            ReleaseM14Object(buffer);
        ReleaseM14Object(g_vfxPeakIndexBuffers[draw]);
        ReleaseM14Object(g_vfxPeakVertexBuffers[draw]);
    }
    ReleaseM14Object(g_vfxPeakSecondaryBuffer);
    ReleaseM14Object(g_m30MainView);
    ReleaseM14Object(g_m30MainTexture);
    for (std::uint32_t packet = 0; packet < g_EndfieldM30PacketCount; ++packet)
    {
        for (ID3D11Buffer*& buffer : g_m30PixelConstantBuffers[packet])
            ReleaseM14Object(buffer);
        for (ID3D11Buffer*& buffer : g_m30VertexConstantBuffers[packet])
            ReleaseM14Object(buffer);
        ReleaseM14Object(g_m30IndexBuffers[packet]);
        ReleaseM14Object(g_m30SecondaryBuffers[packet]);
        ReleaseM14Object(g_m30VertexBuffers[packet]);
    }
    ReleaseM14Object(g_m31PeakRasterizerState);
    ReleaseM14Object(g_m31PeakDepthState);
    ReleaseM14Object(g_m31PeakBlendState);
    for (ID3D11SamplerState*& sampler : g_m31PeakSamplers)
        ReleaseM14Object(sampler);
    ReleaseM14Object(g_m31PeakMainView);
    ReleaseM14Object(g_m31PeakMainTexture);
    for (std::uint32_t packet = 0;
         packet < g_EndfieldM31PeakDrawPayloadCount; ++packet)
    {
        for (ID3D11Buffer*& buffer : g_m31PeakPixelConstantBuffers[packet])
            ReleaseM14Object(buffer);
        for (ID3D11Buffer*& buffer : g_m31PeakVertexConstantBuffers[packet])
            ReleaseM14Object(buffer);
        ReleaseM14Object(g_m31PeakIndexBuffers[packet]);
        ReleaseM14Object(g_m31PeakSecondaryBuffers[packet]);
        ReleaseM14Object(g_m31PeakVertexBuffers[packet]);
    }
    ReleaseM14Object(g_m14RasterizerState);
    ReleaseM14Object(g_m14DepthState);
    ReleaseM14Object(g_m14BlendState);
    for (ID3D11SamplerState*& sampler : g_m14Samplers)
        ReleaseM14Object(sampler);
    ReleaseM14Object(g_m14SkinView);
    ReleaseM14Object(g_m14SkinBuffer);
    for (std::uint32_t packet = 0; packet < g_EndfieldM14PacketCount; ++packet)
    {
        for (ID3D11Buffer*& buffer : g_m14PixelConstantBuffers[packet])
            ReleaseM14Object(buffer);
        for (ID3D11Buffer*& buffer : g_m14VertexConstantBuffers[packet])
            ReleaseM14Object(buffer);
        ReleaseM14Object(g_m14IndexBuffers[packet]);
        ReleaseM14Object(g_m14VertexBuffers[packet]);
    }
    ReleaseM14Object(g_m14DefaultVertexBuffer);
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

std::uint64_t PackOpeningStripDimensions(
    std::uint32_t width,
    std::uint32_t height)
{
    return (static_cast<std::uint64_t>(width) << 32u) |
        static_cast<std::uint64_t>(height);
}

void UnpackOpeningStripDimensions(
    std::uint64_t packed,
    std::uint32_t& width,
    std::uint32_t& height)
{
    width = static_cast<std::uint32_t>(packed >> 32u);
    height = static_cast<std::uint32_t>(packed & 0xffffffffu);
}

bool IsCapturedOpeningStripScreenSize(
    const std::uint8_t* captured,
    std::size_t capturedBytes)
{
    if (captured == nullptr || capturedBytes < sizeof(float) * 4u)
        return false;
    float capturedScreenSize[4] = {};
    std::memcpy(capturedScreenSize, captured, sizeof(capturedScreenSize));
    constexpr float kCapturedWidth = 3840.0f;
    constexpr float kCapturedHeight = 2160.0f;
    constexpr float kTolerance = 0.000001f;
    return capturedScreenSize[0] == kCapturedWidth &&
        capturedScreenSize[1] == kCapturedHeight &&
        std::fabs(capturedScreenSize[2] - 1.0f / kCapturedWidth) <= kTolerance &&
        std::fabs(capturedScreenSize[3] - 1.0f / kCapturedHeight) <= kTolerance;
}

HRESULT CreateOpeningStripConstantBuffer(
    ID3D11Device* device,
    std::uint32_t declaredFloat4Count,
    const std::uint8_t* captured,
    std::size_t capturedBytes,
    bool patchScreenSize,
    std::uint32_t outputWidth,
    std::uint32_t outputHeight,
    ID3D11Buffer** output)
{
    if (!patchScreenSize)
    {
        return CreateM14ConstantBuffer(
            device, declaredFloat4Count, captured, capturedBytes, output);
    }
    if (device == nullptr || output == nullptr || captured == nullptr ||
        declaredFloat4Count == 0 || declaredFloat4Count > 4096 ||
        capturedBytes < sizeof(float) * 4u ||
        capturedBytes > declaredFloat4Count * 16u ||
        outputWidth == 0 || outputHeight == 0)
    {
        return E_INVALIDARG;
    }

    if (!IsCapturedOpeningStripScreenSize(captured, capturedBytes))
    {
        // Reflection identifies ShaderVariablesGlobal._ScreenSize at byte
        // offset zero. Refuse a different capture layout instead of modifying
        // an unverified constant.
        return E_INVALIDARG;
    }

    const UINT byteWidth = declaredFloat4Count * 16u;
    unsigned char* payload = new (std::nothrow) unsigned char[byteWidth]();
    if (payload == nullptr)
        return E_OUTOFMEMORY;
    std::memcpy(payload, captured, capturedBytes);
    const float patchedScreenSize[4] = {
        static_cast<float>(outputWidth),
        static_cast<float>(outputHeight),
        1.0f / static_cast<float>(outputWidth),
        1.0f / static_cast<float>(outputHeight)};
    std::memcpy(payload, patchedScreenSize, sizeof(patchedScreenSize));
    if (std::memcmp(payload, patchedScreenSize, sizeof(patchedScreenSize)) != 0)
    {
        delete[] payload;
        return E_FAIL;
    }
    const HRESULT result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_CONSTANT_BUFFER, payload, byteWidth, output);
    delete[] payload;
    return result;
}

bool IsCapturedM20ScreenConstants(
    const std::uint8_t* captured,
    std::size_t capturedBytes)
{
    if (captured == nullptr || capturedBytes < 6u * sizeof(float) * 4u)
        return false;
    const float* rows = reinterpret_cast<const float*>(captured);
    constexpr float kCapturedWidth = 3840.0f;
    constexpr float kCapturedHeight = 2160.0f;
    constexpr float kTolerance = 0.000001f;
    const auto isScreenSize = [&](std::size_t row)
    {
        const float* value = rows + row * 4u;
        return value[0] == kCapturedWidth && value[1] == kCapturedHeight &&
            std::fabs(value[2] - 1.0f / kCapturedWidth) <= kTolerance &&
            std::fabs(value[3] - 1.0f / kCapturedHeight) <= kTolerance;
    };
    const float* viewport = rows + 5u * 4u;
    return isScreenSize(0u) && isScreenSize(1u) &&
        viewport[0] == kCapturedWidth && viewport[1] == kCapturedHeight &&
        std::fabs(viewport[2] - (1.0f + 1.0f / kCapturedWidth)) <= kTolerance &&
        std::fabs(viewport[3] - (1.0f + 1.0f / kCapturedHeight)) <= kTolerance;
}

HRESULT CreateM20ScreenConstantBuffer(
    ID3D11Device* device,
    std::uint32_t declaredFloat4Count,
    const std::uint8_t* captured,
    std::size_t capturedBytes,
    std::uint32_t outputWidth,
    std::uint32_t outputHeight,
    ID3D11Buffer** output)
{
    if (device == nullptr || output == nullptr || outputWidth == 0 ||
        outputHeight == 0 || declaredFloat4Count == 0 ||
        declaredFloat4Count > 4096 ||
        capturedBytes > declaredFloat4Count * 16u ||
        !IsCapturedM20ScreenConstants(captured, capturedBytes))
        return E_INVALIDARG;
    const UINT byteWidth = declaredFloat4Count * 16u;
    unsigned char* payload = new (std::nothrow) unsigned char[byteWidth]();
    if (payload == nullptr) return E_OUTOFMEMORY;
    std::memcpy(payload, captured, capturedBytes);
    const float screenSize[4] = {
        static_cast<float>(outputWidth), static_cast<float>(outputHeight),
        1.0f / static_cast<float>(outputWidth),
        1.0f / static_cast<float>(outputHeight)};
    const float viewportSize[4] = {
        screenSize[0], screenSize[1], 1.0f + screenSize[2],
        1.0f + screenSize[3]};
    std::memcpy(payload + 0u * 16u, screenSize, sizeof(screenSize));
    std::memcpy(payload + 1u * 16u, screenSize, sizeof(screenSize));
    std::memcpy(payload + 5u * 16u, viewportSize, sizeof(viewportSize));
    const HRESULT result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_CONSTANT_BUFFER, payload, byteWidth, output);
    delete[] payload;
    return result;
}

HRESULT EnsureM20ScreenConstantBuffers(ID3D11Device* device)
{
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    UnpackOpeningStripDimensions(
        g_m20PeakOutputDimensions.load(std::memory_order_acquire), width, height);
    if (width == 0 || height == 0) return E_INVALIDARG;
    if (g_m20PeakScreenSizePatched.load(std::memory_order_acquire) == 1u &&
        g_m20PeakResourceWidth == width && g_m20PeakResourceHeight == height)
        return S_OK;
    ID3D11Buffer* patchedVS = nullptr;
    ID3D11Buffer* patchedPS = nullptr;
    HRESULT result = CreateM20ScreenConstantBuffer(
        device, g_EndfieldM20PeakVSDeclaredFloat4Counts[2],
        g_EndfieldM20PeakVSCB2, g_EndfieldM20PeakVSCB2Size,
        width, height, &patchedVS);
    if (SUCCEEDED(result))
        result = CreateM20ScreenConstantBuffer(
            device, g_EndfieldM20PeakPSDeclaredFloat4Counts[1],
            g_EndfieldM20PeakPSCB1, g_EndfieldM20PeakPSCB1Size,
            width, height, &patchedPS);
    if (FAILED(result))
    {
        ReleaseM14Object(patchedPS);
        ReleaseM14Object(patchedVS);
        return result;
    }
    ReleaseM14Object(g_m20PeakVertexConstantBuffers[2]);
    ReleaseM14Object(g_m20PeakPixelConstantBuffers[1]);
    g_m20PeakVertexConstantBuffers[2] = patchedVS;
    g_m20PeakPixelConstantBuffers[1] = patchedPS;
    g_m20PeakResourceWidth = width;
    g_m20PeakResourceHeight = height;
    g_m20PeakScreenSizePatched.store(1u, std::memory_order_release);
    return S_OK;
}

HRESULT EnsureM18ScreenConstantBuffers(ID3D11Device* device)
{
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    UnpackOpeningStripDimensions(
        g_m18PeakOutputDimensions.load(std::memory_order_acquire), width, height);
    if (width == 0 || height == 0) return E_INVALIDARG;
    if (g_m18PeakScreenSizePatched.load(std::memory_order_acquire) == 1u &&
        g_m18PeakResourceWidth == width && g_m18PeakResourceHeight == height)
        return S_OK;
    ID3D11Buffer* patchedVS = nullptr;
    ID3D11Buffer* patchedPS = nullptr;
    HRESULT result = CreateM20ScreenConstantBuffer(
        device, g_EndfieldM18PeakVSDeclaredFloat4Counts[2],
        g_EndfieldM18PeakVSCB2, g_EndfieldM18PeakVSCB2Size,
        width, height, &patchedVS);
    if (SUCCEEDED(result))
        result = CreateM20ScreenConstantBuffer(
            device, g_EndfieldM18PeakPSDeclaredFloat4Counts[1],
            g_EndfieldM18PeakPSCB1, g_EndfieldM18PeakPSCB1Size,
            width, height, &patchedPS);
    if (FAILED(result))
    {
        ReleaseM14Object(patchedPS);
        ReleaseM14Object(patchedVS);
        return result;
    }
    ReleaseM14Object(g_m18PeakVertexConstantBuffers[2]);
    ReleaseM14Object(g_m18PeakPixelConstantBuffers[1]);
    g_m18PeakVertexConstantBuffers[2] = patchedVS;
    g_m18PeakPixelConstantBuffers[1] = patchedPS;
    g_m18PeakResourceWidth = width;
    g_m18PeakResourceHeight = height;
    g_m18PeakScreenSizePatched.store(1u, std::memory_order_release);
    return S_OK;
}

HRESULT EnsureM28ScreenConstantBuffers(ID3D11Device* device)
{
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    UnpackOpeningStripDimensions(
        g_m28PeakOutputDimensions.load(std::memory_order_acquire), width, height);
    if (width == 0 || height == 0) return E_INVALIDARG;
    if (g_m28PeakScreenSizePatched.load(std::memory_order_acquire) == 1u &&
        g_m28PeakResourceWidth == width && g_m28PeakResourceHeight == height)
        return S_OK;
    ID3D11Buffer* patchedVS = nullptr;
    ID3D11Buffer* patchedPS = nullptr;
    HRESULT result = CreateM20ScreenConstantBuffer(
        device, g_EndfieldM28PeakVSDeclaredFloat4Counts[2],
        g_EndfieldM28PeakVSCB2, g_EndfieldM28PeakVSCB2Size,
        width, height, &patchedVS);
    if (SUCCEEDED(result))
        result = CreateM20ScreenConstantBuffer(
            device, g_EndfieldM28PeakPSDeclaredFloat4Counts[1],
            g_EndfieldM28PeakPSCB1, g_EndfieldM28PeakPSCB1Size,
            width, height, &patchedPS);
    if (FAILED(result))
    {
        ReleaseM14Object(patchedPS);
        ReleaseM14Object(patchedVS);
        return result;
    }
    ReleaseM14Object(g_m28PeakVertexConstantBuffers[2]);
    ReleaseM14Object(g_m28PeakPixelConstantBuffers[1]);
    g_m28PeakVertexConstantBuffers[2] = patchedVS;
    g_m28PeakPixelConstantBuffers[1] = patchedPS;
    g_m28PeakResourceWidth = width;
    g_m28PeakResourceHeight = height;
    g_m28PeakScreenSizePatched.store(1u, std::memory_order_release);
    return S_OK;
}

HRESULT EnsureM14ScreenConstantBuffers(ID3D11Device* device)
{
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    UnpackOpeningStripDimensions(
        g_m14OutputDimensions.load(std::memory_order_acquire), width, height);
    if (width == 0 || height == 0) return E_INVALIDARG;
    if (g_m14ScreenSizePatched.load(std::memory_order_acquire) == 1u &&
        g_m14ResourceWidth == width && g_m14ResourceHeight == height)
        return S_OK;
    ID3D11Buffer* patchedVS[g_EndfieldM14PacketCount] = {};
    ID3D11Buffer* patchedPS[g_EndfieldM14PacketCount] = {};
    HRESULT result = S_OK;
    for (std::uint32_t packetIndex = 0;
         SUCCEEDED(result) && packetIndex < g_EndfieldM14PacketCount;
         ++packetIndex)
    {
        const EndfieldM14PacketPayload& packet = g_EndfieldM14Packets[packetIndex];
        result = CreateM20ScreenConstantBuffer(
            device, g_EndfieldM14VSDeclaredFloat4Counts[2],
            packet.vs[2], packet.vsBytes[2], width, height,
            &patchedVS[packetIndex]);
        if (SUCCEEDED(result))
            result = CreateM20ScreenConstantBuffer(
                device, g_EndfieldM14PSDeclaredFloat4Counts[1],
                packet.ps[1], packet.psBytes[1], width, height,
                &patchedPS[packetIndex]);
    }
    if (FAILED(result))
    {
        for (ID3D11Buffer*& buffer : patchedVS) ReleaseM14Object(buffer);
        for (ID3D11Buffer*& buffer : patchedPS) ReleaseM14Object(buffer);
        return result;
    }
    for (std::uint32_t packetIndex = 0;
         packetIndex < g_EndfieldM14PacketCount; ++packetIndex)
    {
        ReleaseM14Object(g_m14VertexConstantBuffers[packetIndex][2]);
        ReleaseM14Object(g_m14PixelConstantBuffers[packetIndex][1]);
        g_m14VertexConstantBuffers[packetIndex][2] = patchedVS[packetIndex];
        g_m14PixelConstantBuffers[packetIndex][1] = patchedPS[packetIndex];
    }
    g_m14ResourceWidth = width;
    g_m14ResourceHeight = height;
    g_m14ScreenSizePatched.store(1u, std::memory_order_release);
    return S_OK;
}

HRESULT EnsureM21PeakScreenConstantBuffers(ID3D11Device* device)
{
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    UnpackOpeningStripDimensions(
        g_m21PeakOutputDimensions.load(std::memory_order_acquire), width, height);
    if (width == 0 || height == 0) return E_INVALIDARG;
    if (g_m21PeakScreenSizePatched.load(std::memory_order_acquire) == 1u &&
        g_m21PeakResourceWidth == width && g_m21PeakResourceHeight == height)
        return S_OK;
    ID3D11Buffer* patchedVS = nullptr;
    ID3D11Buffer* patchedPS = nullptr;
    HRESULT result = CreateM20ScreenConstantBuffer(
        device, g_EndfieldM21PeakVSDeclaredFloat4Counts[2],
        g_EndfieldM21PeakVSCB2, g_EndfieldM21PeakVSCB2Size,
        width, height, &patchedVS);
    if (SUCCEEDED(result))
        result = CreateM20ScreenConstantBuffer(
            device, g_EndfieldM21PeakPSDeclaredFloat4Counts[1],
            g_EndfieldM21PeakPSCB1, g_EndfieldM21PeakPSCB1Size,
            width, height, &patchedPS);
    if (FAILED(result))
    {
        ReleaseM14Object(patchedPS);
        ReleaseM14Object(patchedVS);
        return result;
    }
    ReleaseM14Object(g_m21PeakVertexConstantBuffers[2]);
    ReleaseM14Object(g_m21PeakPixelConstantBuffers[1]);
    g_m21PeakVertexConstantBuffers[2] = patchedVS;
    g_m21PeakPixelConstantBuffers[1] = patchedPS;
    g_m21PeakResourceWidth = width;
    g_m21PeakResourceHeight = height;
    g_m21PeakScreenSizePatched.store(1u, std::memory_order_release);
    return S_OK;
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
    for (std::uint32_t packetIndex = 0;
         packetIndex < g_EndfieldM14PacketCount;
         ++packetIndex)
    {
        const EndfieldM14PacketPayload& packet =
            g_EndfieldM14Packets[packetIndex];
        result = CreateM14ImmutableBuffer(
            device,
            D3D11_BIND_VERTEX_BUFFER,
            packet.vertices,
            static_cast<UINT>(packet.vertexBytes),
            &g_m14VertexBuffers[packetIndex]);
        if (FAILED(result))
            return result;
        result = CreateM14ImmutableBuffer(
            device,
            D3D11_BIND_INDEX_BUFFER,
            packet.indices,
            static_cast<UINT>(packet.indexBytes),
            &g_m14IndexBuffers[packetIndex]);
        if (FAILED(result))
            return result;
        for (std::size_t slot = 0; slot < 5; ++slot)
        {
            result = CreateM14ConstantBuffer(
                device,
                g_EndfieldM14VSDeclaredFloat4Counts[slot],
                packet.vs[slot],
                packet.vsBytes[slot],
                &g_m14VertexConstantBuffers[packetIndex][slot]);
            if (FAILED(result))
                return result;
        }
        for (std::size_t slot = 0; slot < 4; ++slot)
        {
            result = CreateM14ConstantBuffer(
                device,
                g_EndfieldM14PSDeclaredFloat4Counts[slot],
                packet.ps[slot],
                packet.psBytes[slot],
                &g_m14PixelConstantBuffers[packetIndex][slot]);
            if (FAILED(result))
                return result;
        }
    }

    for (std::uint32_t packetIndex = 0;
         packetIndex < g_EndfieldM31PeakDrawPayloadCount;
         ++packetIndex)
    {
        const EndfieldM31PeakPacketPayload& packet =
            g_EndfieldM31PeakDrawPayloads[packetIndex];
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_VERTEX_BUFFER, packet.vertices,
            static_cast<UINT>(packet.vertexBytes),
            &g_m31PeakVertexBuffers[packetIndex]);
        if (FAILED(result)) return result;
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_VERTEX_BUFFER, packet.secondary,
            static_cast<UINT>(packet.secondaryBytes),
            &g_m31PeakSecondaryBuffers[packetIndex]);
        if (FAILED(result)) return result;
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_INDEX_BUFFER, packet.indices,
            static_cast<UINT>(packet.indexBytes),
            &g_m31PeakIndexBuffers[packetIndex]);
        if (FAILED(result)) return result;
        for (std::size_t slot = 0; slot < 5; ++slot)
        {
            result = CreateM14ConstantBuffer(
                device, g_EndfieldM31PeakVSDeclaredFloat4Counts[slot],
                packet.vs[slot], packet.vsBytes[slot],
                &g_m31PeakVertexConstantBuffers[packetIndex][slot]);
            if (FAILED(result)) return result;
        }
        for (std::size_t slot = 0; slot < 4; ++slot)
        {
            result = CreateM14ConstantBuffer(
                device, g_EndfieldM31PeakPSDeclaredFloat4Counts[slot],
                packet.ps[slot], packet.psBytes[slot],
                &g_m31PeakPixelConstantBuffers[packetIndex][slot]);
            if (FAILED(result)) return result;
        }
    }

    D3D11_TEXTURE2D_DESC m31Texture = {};
    m31Texture.Width = 256u;
    m31Texture.Height = 256u;
    m31Texture.MipLevels = 1u;
    m31Texture.ArraySize = 1u;
    m31Texture.Format = DXGI_FORMAT_BC7_UNORM_SRGB;
    m31Texture.SampleDesc.Count = 1u;
    m31Texture.Usage = D3D11_USAGE_IMMUTABLE;
    m31Texture.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA m31Initial = {};
    m31Initial.pSysMem = g_EndfieldM31PeakTextureT1;
    m31Initial.SysMemPitch = 256u * 4u;
    m31Initial.SysMemSlicePitch =
        static_cast<UINT>(g_EndfieldM31PeakTextureT1Size);
    result = device->CreateTexture2D(
        &m31Texture, &m31Initial, &g_m31PeakMainTexture);
    if (FAILED(result)) return result;
    result = device->CreateShaderResourceView(
        g_m31PeakMainTexture, nullptr, &g_m31PeakMainView);
    if (FAILED(result)) return result;

    // Exact M_fx_endminm_gfx_31 fixed state. The VFXBaseV2 ForwardOnly
    // serialized pass supplies independent MRT blend declarations, while the
    // material supplies the property-backed blend/depth/stencil/cull values.
    D3D11_SAMPLER_DESC m31Sampler = EndfieldM31FixedState::Sampler(0u);
    result = device->CreateSamplerState(
        &m31Sampler, &g_m31PeakSamplers[0]);
    if (FAILED(result)) return result;
    m31Sampler = EndfieldM31FixedState::Sampler(1u);
    result = device->CreateSamplerState(
        &m31Sampler, &g_m31PeakSamplers[1]);
    if (FAILED(result)) return result;

    D3D11_BLEND_DESC m31Blend = EndfieldM31FixedState::Blend();
    result = device->CreateBlendState(&m31Blend, &g_m31PeakBlendState);
    if (FAILED(result)) return result;

    D3D11_DEPTH_STENCIL_DESC m31Depth =
        EndfieldM31FixedState::DepthStencil();
    result = device->CreateDepthStencilState(
        &m31Depth, &g_m31PeakDepthState);
    if (FAILED(result)) return result;

    D3D11_RASTERIZER_DESC m31Rasterizer =
        EndfieldM31FixedState::Rasterizer();
    result = device->CreateRasterizerState(
        &m31Rasterizer, &g_m31PeakRasterizerState);
    if (FAILED(result)) return result;

    result = device->CreateVertexShader(
        g_EndfieldM18PeakVertexDxbc, g_EndfieldM18PeakVertexDxbcSize,
        nullptr, &g_m18PeakVertexShader);
    if (FAILED(result)) return result;
    result = device->CreatePixelShader(
        g_EndfieldM18PeakPixelDxbc, g_EndfieldM18PeakPixelDxbcSize,
        nullptr, &g_m18PeakPixelShader);
    if (FAILED(result)) return result;
    const D3D11_INPUT_ELEMENT_DESC m18Elements[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"NORMAL", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 12,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TANGENT", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 24,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 0, 40,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 1, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 60,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 4, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 60,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDWEIGHTS", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 1, 16,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDINDICES", 0, DXGI_FORMAT_R8G8B8A8_UINT, 1, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
    };
    result = device->CreateInputLayout(
        m18Elements,
        static_cast<UINT>(sizeof(m18Elements) / sizeof(m18Elements[0])),
        g_EndfieldM18PeakVertexDxbc, g_EndfieldM18PeakVertexDxbcSize,
        &g_m18PeakInputLayout);
    if (FAILED(result)) return result;
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_VERTEX_BUFFER, g_EndfieldM18PeakVertices,
        static_cast<UINT>(g_EndfieldM18PeakVerticesSize),
        &g_m18PeakVertexBuffer);
    if (FAILED(result)) return result;
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_VERTEX_BUFFER, g_EndfieldM18PeakSecondary,
        static_cast<UINT>(g_EndfieldM18PeakSecondarySize),
        &g_m18PeakSecondaryBuffer);
    if (FAILED(result)) return result;
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_INDEX_BUFFER, g_EndfieldM18PeakIndices,
        static_cast<UINT>(g_EndfieldM18PeakIndicesSize),
        &g_m18PeakIndexBuffer);
    if (FAILED(result)) return result;
    const std::uint8_t* m18VS[] = {
        g_EndfieldM18PeakVSCB0, g_EndfieldM18PeakVSCB1,
        g_EndfieldM18PeakVSCB2, g_EndfieldM18PeakVSCB3,
        g_EndfieldM18PeakVSCB4,
    };
    const std::size_t m18VSBytes[] = {
        g_EndfieldM18PeakVSCB0Size, g_EndfieldM18PeakVSCB1Size,
        g_EndfieldM18PeakVSCB2Size, g_EndfieldM18PeakVSCB3Size,
        g_EndfieldM18PeakVSCB4Size,
    };
    const std::uint8_t* m18PS[] = {
        g_EndfieldM18PeakPSCB0, g_EndfieldM18PeakPSCB1,
        g_EndfieldM18PeakPSCB2, g_EndfieldM18PeakPSCB3,
    };
    const std::size_t m18PSBytes[] = {
        g_EndfieldM18PeakPSCB0Size, g_EndfieldM18PeakPSCB1Size,
        g_EndfieldM18PeakPSCB2Size, g_EndfieldM18PeakPSCB3Size,
    };
    for (std::size_t slot = 0; slot < 5; ++slot)
    {
        result = CreateM14ConstantBuffer(
            device, g_EndfieldM18PeakVSDeclaredFloat4Counts[slot],
            m18VS[slot], m18VSBytes[slot],
            &g_m18PeakVertexConstantBuffers[slot]);
        if (FAILED(result)) return result;
    }
    for (std::size_t slot = 0; slot < 4; ++slot)
    {
        result = CreateM14ConstantBuffer(
            device, g_EndfieldM18PeakPSDeclaredFloat4Counts[slot],
            m18PS[slot], m18PSBytes[slot],
            &g_m18PeakPixelConstantBuffers[slot]);
        if (FAILED(result)) return result;
    }
    D3D11_SAMPLER_DESC m18Sampler = {};
    m18Sampler.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    m18Sampler.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;
    m18Sampler.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;
    m18Sampler.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    m18Sampler.MaxLOD = 1000.0f;
    for (ID3D11SamplerState*& sampler : g_m18PeakSamplers)
    {
        result = device->CreateSamplerState(&m18Sampler, &sampler);
        if (FAILED(result)) return result;
    }
    D3D11_BLEND_DESC m18Blend = {};
    m18Blend.RenderTarget[0].BlendEnable = TRUE;
    m18Blend.RenderTarget[0].SrcBlend = D3D11_BLEND_ONE;
    m18Blend.RenderTarget[0].DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
    m18Blend.RenderTarget[0].BlendOp = D3D11_BLEND_OP_ADD;
    m18Blend.RenderTarget[0].SrcBlendAlpha = D3D11_BLEND_ONE;
    m18Blend.RenderTarget[0].DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
    m18Blend.RenderTarget[0].BlendOpAlpha = D3D11_BLEND_OP_ADD;
    m18Blend.RenderTarget[0].RenderTargetWriteMask =
        D3D11_COLOR_WRITE_ENABLE_ALL;
    result = device->CreateBlendState(&m18Blend, &g_m18PeakBlendState);
    if (FAILED(result)) return result;
    D3D11_DEPTH_STENCIL_DESC m18Depth = {};
    m18Depth.DepthEnable = TRUE;
    m18Depth.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
    m18Depth.DepthFunc = D3D11_COMPARISON_GREATER_EQUAL;
    m18Depth.StencilEnable = TRUE;
    m18Depth.StencilReadMask = D3D11_DEFAULT_STENCIL_READ_MASK;
    m18Depth.StencilWriteMask = D3D11_DEFAULT_STENCIL_WRITE_MASK;
    m18Depth.FrontFace.StencilFailOp = D3D11_STENCIL_OP_KEEP;
    m18Depth.FrontFace.StencilDepthFailOp = D3D11_STENCIL_OP_KEEP;
    m18Depth.FrontFace.StencilPassOp = D3D11_STENCIL_OP_KEEP;
    m18Depth.FrontFace.StencilFunc = D3D11_COMPARISON_ALWAYS;
    m18Depth.BackFace = m18Depth.FrontFace;
    result = device->CreateDepthStencilState(&m18Depth, &g_m18PeakDepthState);
    if (FAILED(result)) return result;
    D3D11_RASTERIZER_DESC m18Rasterizer = {};
    m18Rasterizer.FillMode = D3D11_FILL_SOLID;
    m18Rasterizer.CullMode = D3D11_CULL_NONE;
    m18Rasterizer.FrontCounterClockwise = TRUE;
    m18Rasterizer.DepthClipEnable = TRUE;
    m18Rasterizer.ScissorEnable = TRUE;
    result = device->CreateRasterizerState(
        &m18Rasterizer, &g_m18PeakRasterizerState);
    if (FAILED(result)) return result;

    result = device->CreateVertexShader(
        g_EndfieldM28PeakVertexDxbc, g_EndfieldM28PeakVertexDxbcSize,
        nullptr, &g_m28PeakVertexShader);
    if (FAILED(result)) return result;
    result = device->CreatePixelShader(
        g_EndfieldM28PeakPixelDxbc, g_EndfieldM28PeakPixelDxbcSize,
        nullptr, &g_m28PeakPixelShader);
    if (FAILED(result)) return result;
    const D3D11_INPUT_ELEMENT_DESC m28Elements[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 0, 24,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 28,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 1, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 4, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDWEIGHTS", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 1, 16,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDINDICES", 0, DXGI_FORMAT_R8G8B8A8_UINT, 1, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
    };
    result = device->CreateInputLayout(
        m28Elements,
        static_cast<UINT>(sizeof(m28Elements) / sizeof(m28Elements[0])),
        g_EndfieldM28PeakVertexDxbc, g_EndfieldM28PeakVertexDxbcSize,
        &g_m28PeakInputLayout);
    if (FAILED(result)) return result;
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_VERTEX_BUFFER, g_EndfieldM28PeakVertices,
        static_cast<UINT>(g_EndfieldM28PeakVerticesSize),
        &g_m28PeakVertexBuffer);
    if (FAILED(result)) return result;
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_VERTEX_BUFFER, g_EndfieldM28PeakSecondary,
        static_cast<UINT>(g_EndfieldM28PeakSecondarySize),
        &g_m28PeakSecondaryBuffer);
    if (FAILED(result)) return result;
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_INDEX_BUFFER, g_EndfieldM28PeakIndices,
        static_cast<UINT>(g_EndfieldM28PeakIndicesSize),
        &g_m28PeakIndexBuffer);
    if (FAILED(result)) return result;
    const std::uint8_t* m28VS[] = {
        g_EndfieldM28PeakVSCB0, g_EndfieldM28PeakVSCB1,
        g_EndfieldM28PeakVSCB2, g_EndfieldM28PeakVSCB3,
        g_EndfieldM28PeakVSCB4,
    };
    const std::size_t m28VSBytes[] = {
        g_EndfieldM28PeakVSCB0Size, g_EndfieldM28PeakVSCB1Size,
        g_EndfieldM28PeakVSCB2Size, g_EndfieldM28PeakVSCB3Size,
        g_EndfieldM28PeakVSCB4Size,
    };
    const std::uint8_t* m28PS[] = {
        g_EndfieldM28PeakPSCB0, g_EndfieldM28PeakPSCB1,
        g_EndfieldM28PeakPSCB2, g_EndfieldM28PeakPSCB3,
    };
    const std::size_t m28PSBytes[] = {
        g_EndfieldM28PeakPSCB0Size, g_EndfieldM28PeakPSCB1Size,
        g_EndfieldM28PeakPSCB2Size, g_EndfieldM28PeakPSCB3Size,
    };
    for (std::size_t slot = 0; slot < 5; ++slot)
    {
        result = CreateM14ConstantBuffer(
            device, g_EndfieldM28PeakVSDeclaredFloat4Counts[slot],
            m28VS[slot], m28VSBytes[slot],
            &g_m28PeakVertexConstantBuffers[slot]);
        if (FAILED(result)) return result;
    }
    for (std::size_t slot = 0; slot < 4; ++slot)
    {
        result = CreateM14ConstantBuffer(
            device, g_EndfieldM28PeakPSDeclaredFloat4Counts[slot],
            m28PS[slot], m28PSBytes[slot],
            &g_m28PeakPixelConstantBuffers[slot]);
        if (FAILED(result)) return result;
    }
    const D3D11_TEXTURE_ADDRESS_MODE m28Addresses[3] = {
        D3D11_TEXTURE_ADDRESS_CLAMP,
        D3D11_TEXTURE_ADDRESS_WRAP,
        D3D11_TEXTURE_ADDRESS_CLAMP,
    };
    for (std::size_t slot = 0; slot < 3; ++slot)
    {
        D3D11_SAMPLER_DESC sampler = {};
        sampler.Filter = D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT;
        sampler.AddressU = m28Addresses[slot];
        sampler.AddressV = m28Addresses[slot];
        sampler.AddressW = m28Addresses[slot];
        sampler.MaxLOD = 1000.0f;
        result = device->CreateSamplerState(
            &sampler, &g_m28PeakSamplers[slot]);
        if (FAILED(result)) return result;
    }
    D3D11_BLEND_DESC m28Blend = {};
    m28Blend.IndependentBlendEnable = TRUE;
    for (std::size_t target = 0; target < 2; ++target)
    {
        D3D11_RENDER_TARGET_BLEND_DESC& blend = m28Blend.RenderTarget[target];
        blend.BlendEnable = TRUE;
        blend.SrcBlend = D3D11_BLEND_SRC_ALPHA;
        blend.DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
        blend.BlendOp = D3D11_BLEND_OP_ADD;
        blend.SrcBlendAlpha = D3D11_BLEND_ONE;
        blend.DestBlendAlpha = D3D11_BLEND_ZERO;
        blend.BlendOpAlpha = D3D11_BLEND_OP_ADD;
        blend.RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
    }
    result = device->CreateBlendState(&m28Blend, &g_m28PeakBlendState);
    if (FAILED(result)) return result;
    D3D11_DEPTH_STENCIL_DESC m28Depth = {};
    m28Depth.DepthEnable = TRUE;
    m28Depth.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
    m28Depth.DepthFunc = D3D11_COMPARISON_ALWAYS;
    result = device->CreateDepthStencilState(&m28Depth, &g_m28PeakDepthState);
    if (FAILED(result)) return result;
    D3D11_RASTERIZER_DESC m28Rasterizer = {};
    m28Rasterizer.FillMode = D3D11_FILL_SOLID;
    m28Rasterizer.CullMode = D3D11_CULL_NONE;
    m28Rasterizer.FrontCounterClockwise = TRUE;
    m28Rasterizer.DepthClipEnable = TRUE;
    m28Rasterizer.ScissorEnable = TRUE;
    result = device->CreateRasterizerState(
        &m28Rasterizer, &g_m28PeakRasterizerState);
    if (FAILED(result)) return result;

    result = device->CreateVertexShader(
        g_EndfieldM21PeakVertexDxbc, g_EndfieldM21PeakVertexDxbcSize,
        nullptr, &g_m21PeakVertexShader);
    if (FAILED(result)) return result;
    result = device->CreatePixelShader(
        g_EndfieldM21PeakPixelDxbc, g_EndfieldM21PeakPixelDxbcSize,
        nullptr, &g_m21PeakPixelShader);
    if (FAILED(result)) return result;
    const D3D11_INPUT_ELEMENT_DESC m21Elements[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"NORMAL", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 12,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TANGENT", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 24,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 0, 40,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 1, DXGI_FORMAT_R32G32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 4, DXGI_FORMAT_R32G32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDWEIGHTS", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 1, 16,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDINDICES", 0, DXGI_FORMAT_R8G8B8A8_UINT, 1, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
    };
    result = device->CreateInputLayout(
        m21Elements,
        static_cast<UINT>(sizeof(m21Elements) / sizeof(m21Elements[0])),
        g_EndfieldM21PeakVertexDxbc, g_EndfieldM21PeakVertexDxbcSize,
        &g_m21PeakInputLayout);
    if (FAILED(result)) return result;
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_VERTEX_BUFFER, g_EndfieldM21PeakVertices,
        static_cast<UINT>(g_EndfieldM21PeakVerticesSize),
        &g_m21PeakVertexBuffer);
    if (FAILED(result)) return result;
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_VERTEX_BUFFER, g_EndfieldM21PeakSecondary,
        static_cast<UINT>(g_EndfieldM21PeakSecondarySize),
        &g_m21PeakSecondaryBuffer);
    if (FAILED(result)) return result;
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_INDEX_BUFFER, g_EndfieldM21PeakIndices,
        static_cast<UINT>(g_EndfieldM21PeakIndicesSize),
        &g_m21PeakIndexBuffer);
    if (FAILED(result)) return result;
    const std::uint8_t* m21VS[] = {
        g_EndfieldM21PeakVSCB0, g_EndfieldM21PeakVSCB1,
        g_EndfieldM21PeakVSCB2, g_EndfieldM21PeakVSCB3,
        g_EndfieldM21PeakVSCB4,
    };
    const std::size_t m21VSBytes[] = {
        g_EndfieldM21PeakVSCB0Size, g_EndfieldM21PeakVSCB1Size,
        g_EndfieldM21PeakVSCB2Size, g_EndfieldM21PeakVSCB3Size,
        g_EndfieldM21PeakVSCB4Size,
    };
    const std::uint8_t* m21PS[] = {
        g_EndfieldM21PeakPSCB0, g_EndfieldM21PeakPSCB1,
        g_EndfieldM21PeakPSCB2, g_EndfieldM21PeakPSCB3,
        g_EndfieldM21PeakPSCB4,
    };
    const std::size_t m21PSBytes[] = {
        g_EndfieldM21PeakPSCB0Size, g_EndfieldM21PeakPSCB1Size,
        g_EndfieldM21PeakPSCB2Size, g_EndfieldM21PeakPSCB3Size,
        g_EndfieldM21PeakPSCB4Size,
    };
    for (std::size_t slot = 0; slot < 5; ++slot)
    {
        result = CreateM14ConstantBuffer(
            device, g_EndfieldM21PeakVSDeclaredFloat4Counts[slot],
            m21VS[slot], m21VSBytes[slot],
            &g_m21PeakVertexConstantBuffers[slot]);
        if (FAILED(result)) return result;
        result = CreateM14ConstantBuffer(
            device, g_EndfieldM21PeakPSDeclaredFloat4Counts[slot],
            m21PS[slot], m21PSBytes[slot],
            &g_m21PeakPixelConstantBuffers[slot]);
        if (FAILED(result)) return result;
    }
    const std::uint32_t whitePixels[16] = {
        0xffffffffu, 0xffffffffu, 0xffffffffu, 0xffffffffu,
        0xffffffffu, 0xffffffffu, 0xffffffffu, 0xffffffffu,
        0xffffffffu, 0xffffffffu, 0xffffffffu, 0xffffffffu,
        0xffffffffu, 0xffffffffu, 0xffffffffu, 0xffffffffu,
    };
    D3D11_TEXTURE2D_DESC m21Texture = {};
    m21Texture.Width = 4u;
    m21Texture.Height = 4u;
    m21Texture.MipLevels = 1u;
    m21Texture.ArraySize = 1u;
    m21Texture.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    m21Texture.SampleDesc.Count = 1u;
    m21Texture.Usage = D3D11_USAGE_IMMUTABLE;
    m21Texture.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA m21Initial = {};
    m21Initial.pSysMem = whitePixels;
    m21Initial.SysMemPitch = 16u;
    m21Initial.SysMemSlicePitch = sizeof(whitePixels);
    result = device->CreateTexture2D(
        &m21Texture, &m21Initial, &g_m21PeakWhiteTexture);
    if (FAILED(result)) return result;
    result = device->CreateShaderResourceView(
        g_m21PeakWhiteTexture, nullptr, &g_m21PeakWhiteView);
    if (FAILED(result)) return result;
    D3D11_SAMPLER_DESC m21Sampler = {};
    m21Sampler.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    m21Sampler.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;
    m21Sampler.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;
    m21Sampler.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    m21Sampler.MaxLOD = 1000.0f;
    result = device->CreateSamplerState(&m21Sampler, &g_m21PeakSampler);
    if (FAILED(result)) return result;
    D3D11_BLEND_DESC m21Blend = {};
    m21Blend.RenderTarget[0].BlendEnable = TRUE;
    m21Blend.RenderTarget[0].SrcBlend = D3D11_BLEND_ONE;
    m21Blend.RenderTarget[0].DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
    m21Blend.RenderTarget[0].BlendOp = D3D11_BLEND_OP_ADD;
    m21Blend.RenderTarget[0].SrcBlendAlpha = D3D11_BLEND_ONE;
    m21Blend.RenderTarget[0].DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
    m21Blend.RenderTarget[0].BlendOpAlpha = D3D11_BLEND_OP_ADD;
    m21Blend.RenderTarget[0].RenderTargetWriteMask =
        D3D11_COLOR_WRITE_ENABLE_ALL;
    result = device->CreateBlendState(&m21Blend, &g_m21PeakBlendState);
    if (FAILED(result)) return result;
    D3D11_DEPTH_STENCIL_DESC m21Depth = {};
    m21Depth.DepthEnable = TRUE;
    m21Depth.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
    m21Depth.DepthFunc = D3D11_COMPARISON_GREATER_EQUAL;
    m21Depth.StencilEnable = TRUE;
    m21Depth.StencilReadMask = D3D11_DEFAULT_STENCIL_READ_MASK;
    m21Depth.StencilWriteMask = D3D11_DEFAULT_STENCIL_WRITE_MASK;
    m21Depth.FrontFace.StencilFailOp = D3D11_STENCIL_OP_KEEP;
    m21Depth.FrontFace.StencilDepthFailOp = D3D11_STENCIL_OP_KEEP;
    m21Depth.FrontFace.StencilPassOp = D3D11_STENCIL_OP_KEEP;
    m21Depth.FrontFace.StencilFunc = D3D11_COMPARISON_ALWAYS;
    m21Depth.BackFace = m21Depth.FrontFace;
    result = device->CreateDepthStencilState(&m21Depth, &g_m21PeakDepthState);
    if (FAILED(result)) return result;
    D3D11_RASTERIZER_DESC m21Rasterizer = {};
    m21Rasterizer.FillMode = D3D11_FILL_SOLID;
    m21Rasterizer.CullMode = D3D11_CULL_NONE;
    m21Rasterizer.FrontCounterClockwise = TRUE;
    m21Rasterizer.DepthClipEnable = TRUE;
    m21Rasterizer.ScissorEnable = TRUE;
    result = device->CreateRasterizerState(
        &m21Rasterizer, &g_m21PeakRasterizerState);
    if (FAILED(result)) return result;

    result = device->CreateVertexShader(
        g_EndfieldM20PeakVertexDxbc, g_EndfieldM20PeakVertexDxbcSize,
        nullptr, &g_m20PeakVertexShader);
    if (FAILED(result)) return result;
    result = device->CreatePixelShader(
        g_EndfieldM20PeakPixelDxbc, g_EndfieldM20PeakPixelDxbcSize,
        nullptr, &g_m20PeakPixelShader);
    if (FAILED(result)) return result;
    const D3D11_INPUT_ELEMENT_DESC m20Elements[] = {
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
        m20Elements, static_cast<UINT>(sizeof(m20Elements) / sizeof(m20Elements[0])),
        g_EndfieldM20PeakVertexDxbc, g_EndfieldM20PeakVertexDxbcSize,
        &g_m20PeakInputLayout);
    if (FAILED(result)) return result;
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_VERTEX_BUFFER, g_EndfieldM20PeakVertices,
        static_cast<UINT>(g_EndfieldM20PeakVerticesSize), &g_m20PeakVertexBuffer);
    if (FAILED(result)) return result;
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_VERTEX_BUFFER, g_EndfieldM20PeakSecondary,
        static_cast<UINT>(g_EndfieldM20PeakSecondarySize),
        &g_m20PeakSecondaryBuffer);
    if (FAILED(result)) return result;
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_INDEX_BUFFER, g_EndfieldM20PeakIndices,
        static_cast<UINT>(g_EndfieldM20PeakIndicesSize), &g_m20PeakIndexBuffer);
    if (FAILED(result)) return result;
    D3D11_BUFFER_DESC m20VertexResource = {};
    m20VertexResource.ByteWidth = static_cast<UINT>(g_EndfieldM20PeakVertexResourceSize);
    m20VertexResource.Usage = D3D11_USAGE_IMMUTABLE;
    m20VertexResource.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    m20VertexResource.MiscFlags = D3D11_RESOURCE_MISC_BUFFER_ALLOW_RAW_VIEWS;
    D3D11_SUBRESOURCE_DATA m20VertexInitial = {};
    m20VertexInitial.pSysMem = g_EndfieldM20PeakVertexResource;
    result = device->CreateBuffer(
        &m20VertexResource, &m20VertexInitial, &g_m20PeakVertexResource);
    if (FAILED(result)) return result;
    D3D11_SHADER_RESOURCE_VIEW_DESC m20VertexView = {};
    m20VertexView.Format = DXGI_FORMAT_R32_TYPELESS;
    m20VertexView.ViewDimension = D3D11_SRV_DIMENSION_BUFFEREX;
    m20VertexView.BufferEx.NumElements = m20VertexResource.ByteWidth / 4u;
    m20VertexView.BufferEx.Flags = D3D11_BUFFEREX_SRV_FLAG_RAW;
    result = device->CreateShaderResourceView(
        g_m20PeakVertexResource, &m20VertexView, &g_m20PeakVertexView);
    if (FAILED(result)) return result;
    const std::uint8_t* m20VS[] = {
        g_EndfieldM20PeakVSCB0, g_EndfieldM20PeakVSCB1,
        g_EndfieldM20PeakVSCB2, g_EndfieldM20PeakVSCB3,
        g_EndfieldM20PeakVSCB4,
    };
    const std::size_t m20VSBytes[] = {
        g_EndfieldM20PeakVSCB0Size, g_EndfieldM20PeakVSCB1Size,
        g_EndfieldM20PeakVSCB2Size, g_EndfieldM20PeakVSCB3Size,
        g_EndfieldM20PeakVSCB4Size,
    };
    const std::uint8_t* m20PS[] = {
        g_EndfieldM20PeakPSCB0, g_EndfieldM20PeakPSCB1,
        g_EndfieldM20PeakPSCB2, g_EndfieldM20PeakPSCB3,
    };
    const std::size_t m20PSBytes[] = {
        g_EndfieldM20PeakPSCB0Size, g_EndfieldM20PeakPSCB1Size,
        g_EndfieldM20PeakPSCB2Size, g_EndfieldM20PeakPSCB3Size,
    };
    for (std::size_t slot = 0; slot < 5; ++slot)
    {
        result = CreateM14ConstantBuffer(
            device, g_EndfieldM20PeakVSDeclaredFloat4Counts[slot],
            m20VS[slot], m20VSBytes[slot], &g_m20PeakVertexConstantBuffers[slot]);
        if (FAILED(result)) return result;
    }
    for (std::size_t slot = 0; slot < 4; ++slot)
    {
        result = CreateM14ConstantBuffer(
            device, g_EndfieldM20PeakPSDeclaredFloat4Counts[slot],
            m20PS[slot], m20PSBytes[slot], &g_m20PeakPixelConstantBuffers[slot]);
        if (FAILED(result)) return result;
    }
    D3D11_TEXTURE2D_DESC m20Atlas = {};
    m20Atlas.Width = g_EndfieldM20PeakAtlasWidth;
    m20Atlas.Height = g_EndfieldM20PeakAtlasHeight;
    m20Atlas.MipLevels = 1u;
    m20Atlas.ArraySize = 1u;
    m20Atlas.Format = DXGI_FORMAT_BC7_UNORM_SRGB;
    m20Atlas.SampleDesc.Count = 1u;
    m20Atlas.Usage = D3D11_USAGE_IMMUTABLE;
    m20Atlas.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA m20AtlasInitial = {};
    m20AtlasInitial.pSysMem = g_EndfieldM20PeakAtlasBc7;
    m20AtlasInitial.SysMemPitch = ((m20Atlas.Width + 3u) / 4u) * 16u;
    m20AtlasInitial.SysMemSlicePitch = static_cast<UINT>(g_EndfieldM20PeakAtlasBc7Size);
    result = device->CreateTexture2D(
        &m20Atlas, &m20AtlasInitial, &g_m20PeakAtlasTexture);
    if (FAILED(result)) return result;
    result = device->CreateShaderResourceView(
        g_m20PeakAtlasTexture, nullptr, &g_m20PeakAtlasView);
    if (FAILED(result)) return result;
    const D3D11_FILTER m20Filters[2] = {
        D3D11_FILTER_MIN_MAG_MIP_POINT,
        D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT,
    };
    const D3D11_TEXTURE_ADDRESS_MODE m20Addresses[2] = {
        D3D11_TEXTURE_ADDRESS_CLAMP, D3D11_TEXTURE_ADDRESS_WRAP,
    };
    for (std::size_t slot = 0; slot < 2; ++slot)
    {
        D3D11_SAMPLER_DESC sampler = {};
        sampler.Filter = m20Filters[slot];
        sampler.AddressU = m20Addresses[slot];
        sampler.AddressV = m20Addresses[slot];
        sampler.AddressW = m20Addresses[slot];
        sampler.MaxLOD = 1000.0f;
        result = device->CreateSamplerState(&sampler, &g_m20PeakSamplers[slot]);
        if (FAILED(result)) return result;
    }
    D3D11_BLEND_DESC m20Blend = {};
    m20Blend.IndependentBlendEnable = TRUE;
    for (std::size_t target = 0; target < 2; ++target)
    {
        D3D11_RENDER_TARGET_BLEND_DESC& blend = m20Blend.RenderTarget[target];
        blend.BlendEnable = TRUE;
        blend.SrcBlend = D3D11_BLEND_ONE;
        blend.DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
        blend.BlendOp = D3D11_BLEND_OP_ADD;
        blend.SrcBlendAlpha = D3D11_BLEND_ONE;
        blend.DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
        blend.BlendOpAlpha = D3D11_BLEND_OP_ADD;
        blend.RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
    }
    result = device->CreateBlendState(&m20Blend, &g_m20PeakBlendState);
    if (FAILED(result)) return result;
    D3D11_DEPTH_STENCIL_DESC m20Depth = {};
    m20Depth.DepthEnable = TRUE;
    m20Depth.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
    m20Depth.DepthFunc = D3D11_COMPARISON_GREATER_EQUAL;
    m20Depth.StencilEnable = TRUE;
    m20Depth.StencilReadMask = D3D11_DEFAULT_STENCIL_READ_MASK;
    m20Depth.StencilWriteMask = D3D11_DEFAULT_STENCIL_WRITE_MASK;
    m20Depth.FrontFace.StencilFailOp = D3D11_STENCIL_OP_KEEP;
    m20Depth.FrontFace.StencilDepthFailOp = D3D11_STENCIL_OP_KEEP;
    m20Depth.FrontFace.StencilPassOp = D3D11_STENCIL_OP_KEEP;
    m20Depth.FrontFace.StencilFunc = D3D11_COMPARISON_ALWAYS;
    m20Depth.BackFace = m20Depth.FrontFace;
    result = device->CreateDepthStencilState(&m20Depth, &g_m20PeakDepthState);
    if (FAILED(result)) return result;
    D3D11_RASTERIZER_DESC m20Rasterizer = {};
    m20Rasterizer.FillMode = D3D11_FILL_SOLID;
    m20Rasterizer.CullMode = D3D11_CULL_NONE;
    m20Rasterizer.FrontCounterClockwise = TRUE;
    m20Rasterizer.DepthClipEnable = TRUE;
    m20Rasterizer.ScissorEnable = TRUE;
    result = device->CreateRasterizerState(
        &m20Rasterizer, &g_m20PeakRasterizerState);
    if (FAILED(result)) return result;

    for (std::uint32_t packetIndex = 0;
         packetIndex < g_EndfieldM30PacketCount; ++packetIndex)
    {
        const EndfieldM30PacketPayload& packet = g_EndfieldM30Packets[packetIndex];
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_VERTEX_BUFFER, packet.vertices,
            static_cast<UINT>(packet.vertexBytes), &g_m30VertexBuffers[packetIndex]);
        if (FAILED(result)) return result;
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_VERTEX_BUFFER, packet.secondary,
            static_cast<UINT>(packet.secondaryBytes),
            &g_m30SecondaryBuffers[packetIndex]);
        if (FAILED(result)) return result;
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_INDEX_BUFFER, packet.indices,
            static_cast<UINT>(packet.indexBytes), &g_m30IndexBuffers[packetIndex]);
        if (FAILED(result)) return result;
        for (std::size_t slot = 0; slot < 5; ++slot)
        {
            result = CreateM14ConstantBuffer(
                device, g_EndfieldM30VSDeclaredFloat4Counts[slot],
                packet.vs[slot], packet.vsBytes[slot],
                &g_m30VertexConstantBuffers[packetIndex][slot]);
            if (FAILED(result)) return result;
        }
        for (std::size_t slot = 0; slot < 4; ++slot)
        {
            result = CreateM14ConstantBuffer(
                device, g_EndfieldM30PSDeclaredFloat4Counts[slot],
                packet.ps[slot], packet.psBytes[slot],
                &g_m30PixelConstantBuffers[packetIndex][slot]);
            if (FAILED(result)) return result;
        }
    }

    D3D11_TEXTURE2D_DESC m30Texture = {};
    m30Texture.Width = g_EndfieldM30TextureWidth;
    m30Texture.Height = g_EndfieldM30TextureHeight;
    m30Texture.MipLevels = 1u;
    m30Texture.ArraySize = 1u;
    m30Texture.Format = DXGI_FORMAT_BC7_UNORM_SRGB;
    m30Texture.SampleDesc.Count = 1u;
    m30Texture.Usage = D3D11_USAGE_IMMUTABLE;
    m30Texture.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA m30Initial = {};
    m30Initial.pSysMem = g_EndfieldM30TextureT1;
    m30Initial.SysMemPitch = g_EndfieldM30TextureWidth * 4u;
    m30Initial.SysMemSlicePitch = static_cast<UINT>(g_EndfieldM30TextureT1Size);
    result = device->CreateTexture2D(&m30Texture, &m30Initial, &g_m30MainTexture);
    if (FAILED(result)) return result;
    result = device->CreateShaderResourceView(
        g_m30MainTexture, nullptr, &g_m30MainView);
    if (FAILED(result)) return result;

    for (std::uint32_t drawIndex = 0;
         drawIndex < g_EndfieldVFXPeakDrawCount; ++drawIndex)
    {
        const EndfieldVFXPeakDrawPayload& draw =
            g_EndfieldVFXPeakDraws[drawIndex];
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_VERTEX_BUFFER, draw.vertices,
            static_cast<UINT>(draw.vertexBytes),
            &g_vfxPeakVertexBuffers[drawIndex]);
        if (FAILED(result)) return result;
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_INDEX_BUFFER, draw.indices,
            static_cast<UINT>(draw.indexBytes),
            &g_vfxPeakIndexBuffers[drawIndex]);
        if (FAILED(result)) return result;
        for (std::size_t slot = 0; slot < 5; ++slot)
        {
            result = CreateM14ConstantBuffer(
                device, g_EndfieldVFXPeakVSDeclaredFloat4Counts[slot],
                draw.vs[slot], draw.vsBytes[slot],
                &g_vfxPeakVertexConstantBuffers[drawIndex][slot]);
            if (FAILED(result)) return result;
        }
        for (std::size_t slot = 0; slot < 4; ++slot)
        {
            result = CreateM14ConstantBuffer(
                device, g_EndfieldVFXPeakPSDeclaredFloat4Counts[slot],
                draw.ps[slot], draw.psBytes[slot],
                &g_vfxPeakPixelConstantBuffers[drawIndex][slot]);
            if (FAILED(result)) return result;
        }
    }
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_VERTEX_BUFFER, g_EndfieldVFXPeakSecondary,
        static_cast<UINT>(g_EndfieldVFXPeakSecondarySize),
        &g_vfxPeakSecondaryBuffer);
    if (FAILED(result)) return result;
    for (std::uint32_t textureIndex = 0;
         textureIndex < g_EndfieldVFXPeakTextureCount; ++textureIndex)
    {
        const EndfieldVFXPeakTexturePayload& payload =
            g_EndfieldVFXPeakTextures[textureIndex];
        D3D11_TEXTURE2D_DESC texture = {};
        texture.Width = payload.width;
        texture.Height = payload.height;
        texture.MipLevels = 1u;
        texture.ArraySize = 1u;
        texture.Format = DXGI_FORMAT_BC7_UNORM_SRGB;
        texture.SampleDesc.Count = 1u;
        texture.Usage = D3D11_USAGE_IMMUTABLE;
        texture.BindFlags = D3D11_BIND_SHADER_RESOURCE;
        D3D11_SUBRESOURCE_DATA initial = {};
        initial.pSysMem = payload.data;
        initial.SysMemPitch = ((payload.width + 3u) / 4u) * 16u;
        initial.SysMemSlicePitch = static_cast<UINT>(payload.bytes);
        result = device->CreateTexture2D(
            &texture, &initial, &g_vfxPeakTextures[textureIndex]);
        if (FAILED(result)) return result;
        result = device->CreateShaderResourceView(
            g_vfxPeakTextures[textureIndex], nullptr,
            &g_vfxPeakTextureViews[textureIndex]);
        if (FAILED(result)) return result;
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
    // Full retail frame 20260828T004942Z/2775 closes the formerly guessed
    // M13 addressing contract: s0 wraps while s1 and s2 clamp. The authored
    // auxiliary mask slots follow the same clamp policy as s1/s2.
    sampler.AddressU = D3D11_TEXTURE_ADDRESS_WRAP;
    sampler.AddressV = D3D11_TEXTURE_ADDRESS_WRAP;
    sampler.AddressW = D3D11_TEXTURE_ADDRESS_WRAP;
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
    if (FAILED(result))
        return result;

    D3D11_SAMPLER_DESC peakSampler = {};
    peakSampler.Filter = D3D11_FILTER_MIN_MAG_MIP_POINT;
    peakSampler.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;
    peakSampler.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;
    peakSampler.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    peakSampler.MaxLOD = 1000.0f;
    result = device->CreateSamplerState(
        &peakSampler, &g_vfxPeakSamplers[0]);
    if (FAILED(result)) return result;
    peakSampler.Filter = D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT;
    peakSampler.AddressU = D3D11_TEXTURE_ADDRESS_WRAP;
    peakSampler.AddressV = D3D11_TEXTURE_ADDRESS_WRAP;
    peakSampler.AddressW = D3D11_TEXTURE_ADDRESS_WRAP;
    result = device->CreateSamplerState(
        &peakSampler, &g_vfxPeakSamplers[1]);
    if (FAILED(result)) return result;

    D3D11_BLEND_DESC peakBlend = {};
    peakBlend.IndependentBlendEnable = TRUE;
    for (std::size_t target = 0; target < 2; ++target)
    {
        peakBlend.RenderTarget[target].BlendEnable = TRUE;
        peakBlend.RenderTarget[target].SrcBlend = D3D11_BLEND_ONE;
        peakBlend.RenderTarget[target].DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
        peakBlend.RenderTarget[target].BlendOp = D3D11_BLEND_OP_ADD;
        peakBlend.RenderTarget[target].SrcBlendAlpha = D3D11_BLEND_ONE;
        peakBlend.RenderTarget[target].DestBlendAlpha =
            D3D11_BLEND_INV_SRC_ALPHA;
        peakBlend.RenderTarget[target].BlendOpAlpha = D3D11_BLEND_OP_ADD;
        peakBlend.RenderTarget[target].RenderTargetWriteMask =
            D3D11_COLOR_WRITE_ENABLE_ALL;
    }
    result = device->CreateBlendState(&peakBlend, &g_vfxPeakBlendState);
    if (FAILED(result)) return result;

    D3D11_DEPTH_STENCIL_DESC peakDepth = {};
    peakDepth.DepthEnable = TRUE;
    peakDepth.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
    peakDepth.DepthFunc = D3D11_COMPARISON_GREATER_EQUAL;
    peakDepth.StencilEnable = TRUE;
    peakDepth.StencilReadMask = D3D11_DEFAULT_STENCIL_READ_MASK;
    peakDepth.StencilWriteMask = D3D11_DEFAULT_STENCIL_WRITE_MASK;
    peakDepth.FrontFace.StencilFailOp = D3D11_STENCIL_OP_KEEP;
    peakDepth.FrontFace.StencilDepthFailOp = D3D11_STENCIL_OP_KEEP;
    peakDepth.FrontFace.StencilPassOp = D3D11_STENCIL_OP_KEEP;
    peakDepth.FrontFace.StencilFunc = D3D11_COMPARISON_ALWAYS;
    peakDepth.BackFace = peakDepth.FrontFace;
    result = device->CreateDepthStencilState(
        &peakDepth, &g_vfxPeakDepthState);
    if (FAILED(result)) return result;

    D3D11_RASTERIZER_DESC peakRasterizer = {};
    peakRasterizer.FillMode = D3D11_FILL_SOLID;
    peakRasterizer.CullMode = D3D11_CULL_NONE;
    peakRasterizer.FrontCounterClockwise = TRUE;
    peakRasterizer.DepthClipEnable = TRUE;
    peakRasterizer.ScissorEnable = TRUE;
    return device->CreateRasterizerState(
        &peakRasterizer, &g_vfxPeakRasterizerState);
}

void ReleaseM13RuntimeResources()
{
    g_m13ScreenSizePatched.store(0, std::memory_order_release);
    g_m13ResourceWidth = 0;
    g_m13ResourceHeight = 0;
    ReleaseM14Object(g_m13RasterizerState);
    ReleaseM14Object(g_m13DepthState);
    ReleaseM14Object(g_m13BlendState);
    for (ID3D11SamplerState*& sampler : g_m13Samplers)
        ReleaseM14Object(sampler);
    for (ID3D11ShaderResourceView*& view : g_m13TextureViews)
        ReleaseM14Object(view);
    for (ID3D11Texture2D*& texture : g_m13Textures)
        ReleaseM14Object(texture);
    ReleaseM14Object(g_m13SkinView);
    ReleaseM14Object(g_m13SkinBuffer);
    for (auto& packet : g_m13PixelConstantBuffers)
        for (ID3D11Buffer*& buffer : packet)
            ReleaseM14Object(buffer);
    for (auto& packet : g_m13VertexConstantBuffers)
        for (ID3D11Buffer*& buffer : packet)
            ReleaseM14Object(buffer);
    ReleaseM14Object(g_m13IndexBuffer);
    ReleaseM14Object(g_m13DefaultVertexBuffer);
    for (ID3D11Buffer*& buffer : g_m13VertexBuffers)
        ReleaseM14Object(buffer);
    ReleaseM14Object(g_m13InputLayout);
    ReleaseM14Object(g_m13RuntimePixelShader);
    ReleaseM14Object(g_m13RuntimeVertexShader);
}

HRESULT EnsureM13ScreenConstantBuffers(ID3D11Device* device)
{
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    UnpackOpeningStripDimensions(
        g_m13OutputDimensions.load(std::memory_order_acquire), width, height);
    if (width == 0 || height == 0) return E_INVALIDARG;
    if (g_m13ScreenSizePatched.load(std::memory_order_acquire) == 1u &&
        g_m13ResourceWidth == width && g_m13ResourceHeight == height)
        return S_OK;
    ID3D11Buffer* patchedVS[g_EndfieldM13PacketCount] = {};
    ID3D11Buffer* patchedPS[g_EndfieldM13PacketCount] = {};
    HRESULT result = S_OK;
    for (std::uint32_t packetIndex = 0;
         SUCCEEDED(result) && packetIndex < g_EndfieldM13PacketCount;
         ++packetIndex)
    {
        const EndfieldM13PacketPayload& packet =
            g_EndfieldM13Packets[packetIndex];
        result = CreateM20ScreenConstantBuffer(
            device, g_EndfieldM13VSDeclaredFloat4Counts[2],
            packet.vs[2], packet.vsBytes[2], width, height,
            &patchedVS[packetIndex]);
        if (SUCCEEDED(result))
            result = CreateM20ScreenConstantBuffer(
                device, g_EndfieldM13PSDeclaredFloat4Counts[1],
                packet.ps[1], packet.psBytes[1], width, height,
                &patchedPS[packetIndex]);
    }
    if (FAILED(result))
    {
        for (ID3D11Buffer*& buffer : patchedVS) ReleaseM14Object(buffer);
        for (ID3D11Buffer*& buffer : patchedPS) ReleaseM14Object(buffer);
        return result;
    }
    for (std::uint32_t packetIndex = 0;
         packetIndex < g_EndfieldM13PacketCount; ++packetIndex)
    {
        ReleaseM14Object(g_m13VertexConstantBuffers[packetIndex][2]);
        ReleaseM14Object(g_m13PixelConstantBuffers[packetIndex][1]);
        g_m13VertexConstantBuffers[packetIndex][2] = patchedVS[packetIndex];
        g_m13PixelConstantBuffers[packetIndex][1] = patchedPS[packetIndex];
    }
    g_m13ResourceWidth = width;
    g_m13ResourceHeight = height;
    g_m13ScreenSizePatched.store(1u, std::memory_order_release);
    return S_OK;
}

HRESULT CreateM13Texture(
    ID3D11Device* device,
    const EndfieldM13TexturePayload& payload,
    ID3D11Texture2D** texture,
    ID3D11ShaderResourceView** view)
{
    if (device == nullptr || payload.bytes == nullptr || payload.width == 0 ||
        payload.height == 0 || texture == nullptr || view == nullptr ||
        payload.width % 4u != 0 || payload.height % 4u != 0 ||
        payload.size != static_cast<std::size_t>(payload.width) * payload.height)
        return E_INVALIDARG;
    D3D11_TEXTURE2D_DESC description = {};
    description.Width = payload.width;
    description.Height = payload.height;
    description.MipLevels = 1;
    description.ArraySize = 1;
    description.Format = DXGI_FORMAT_BC7_UNORM_SRGB;
    description.SampleDesc.Count = 1;
    description.Usage = D3D11_USAGE_IMMUTABLE;
    description.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA initial = {};
    initial.pSysMem = payload.bytes;
    initial.SysMemPitch = payload.width * 4u;
    initial.SysMemSlicePitch = static_cast<UINT>(payload.size);
    HRESULT result = device->CreateTexture2D(&description, &initial, texture);
    if (FAILED(result))
        return result;
    result = device->CreateShaderResourceView(*texture, nullptr, view);
    if (FAILED(result))
        ReleaseM14Object(*texture);
    return result;
}

HRESULT CreateM13RuntimeResources(ID3D11Device* device)
{
    if (device == nullptr)
        return E_POINTER;
    if (g_m13RuntimeVertexShader != nullptr &&
        g_m13RuntimePixelShader != nullptr)
        return S_OK;

    ReleaseM13RuntimeResources();
    HRESULT result = device->CreateVertexShader(
        g_EndfieldM13VertexDxbc,
        g_EndfieldM13VertexDxbcSize,
        nullptr,
        &g_m13RuntimeVertexShader);
    if (FAILED(result))
        return result;
    result = device->CreatePixelShader(
        g_EndfieldM13PixelDxbc,
        g_EndfieldM13PixelDxbcSize,
        nullptr,
        &g_m13RuntimePixelShader);
    if (FAILED(result))
        return result;

    const D3D11_INPUT_ELEMENT_DESC elements[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 0, 24,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 28,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 1, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 4, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDWEIGHTS", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 1, 16,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDINDICES", 0, DXGI_FORMAT_R8G8B8A8_UINT, 1, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
    };
    result = device->CreateInputLayout(
        elements,
        static_cast<UINT>(sizeof(elements) / sizeof(elements[0])),
        g_EndfieldM13VertexDxbc,
        g_EndfieldM13VertexDxbcSize,
        &g_m13InputLayout);
    if (FAILED(result))
        return result;

    for (std::size_t packetIndex = 0;
         packetIndex < g_EndfieldM13PacketCount; ++packetIndex)
    {
        const EndfieldM13PacketPayload& packet =
            g_EndfieldM13Packets[packetIndex];
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_VERTEX_BUFFER, packet.vertices,
            static_cast<UINT>(packet.vertexBytes),
            &g_m13VertexBuffers[packetIndex]);
        if (FAILED(result))
            return result;
    }
    const unsigned char defaultVertex[20] = {};
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_VERTEX_BUFFER, defaultVertex,
        sizeof(defaultVertex), &g_m13DefaultVertexBuffer);
    if (FAILED(result))
        return result;
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_INDEX_BUFFER, g_EndfieldM13Indices,
        static_cast<UINT>(g_EndfieldM13IndicesSize), &g_m13IndexBuffer);
    if (FAILED(result))
        return result;
    for (std::size_t packetIndex = 0;
         packetIndex < g_EndfieldM13PacketCount; ++packetIndex)
    {
        const EndfieldM13PacketPayload& packet =
            g_EndfieldM13Packets[packetIndex];
        for (std::size_t slot = 0; slot < 5; ++slot)
        {
            result = CreateM14ConstantBuffer(
                device, g_EndfieldM13VSDeclaredFloat4Counts[slot],
                packet.vs[slot], packet.vsBytes[slot],
                &g_m13VertexConstantBuffers[packetIndex][slot]);
            if (FAILED(result))
                return result;
        }
        for (std::size_t slot = 0; slot < 4; ++slot)
        {
            result = CreateM14ConstantBuffer(
                device, g_EndfieldM13PSDeclaredFloat4Counts[slot],
                packet.ps[slot], packet.psBytes[slot],
                &g_m13PixelConstantBuffers[packetIndex][slot]);
            if (FAILED(result))
                return result;
        }
    }

    const float zeroSkin[4] = {};
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_SHADER_RESOURCE, zeroSkin, sizeof(zeroSkin),
        &g_m13SkinBuffer, D3D11_RESOURCE_MISC_BUFFER_STRUCTURED,
        sizeof(zeroSkin));
    if (FAILED(result))
        return result;
    result = device->CreateShaderResourceView(
        g_m13SkinBuffer, nullptr, &g_m13SkinView);
    if (FAILED(result))
        return result;
    for (std::size_t slot = 0; slot < 5; ++slot)
    {
        result = CreateM13Texture(
            device, g_EndfieldM13Textures[slot],
            &g_m13Textures[slot], &g_m13TextureViews[slot]);
        if (FAILED(result))
            return result;
    }

    D3D11_SAMPLER_DESC sampler = {};
    sampler.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    sampler.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.MaxLOD = D3D11_FLOAT32_MAX;
    result = device->CreateSamplerState(&sampler, &g_m13Samplers[0]);
    if (FAILED(result))
        return result;
    // Retail M13 draw 75 binds Clamp at s0 and Wrap at s1/s2. The
    // recovered replay previously left every slot clamped, which turns the
    // burst shell into an unnaturally continuous outer ring.
    sampler.AddressU = D3D11_TEXTURE_ADDRESS_WRAP;
    sampler.AddressV = D3D11_TEXTURE_ADDRESS_WRAP;
    sampler.AddressW = D3D11_TEXTURE_ADDRESS_WRAP;
    for (std::size_t slot = 1; slot <= 2; ++slot)
    {
        result = device->CreateSamplerState(&sampler, &g_m13Samplers[slot]);
        if (FAILED(result))
            return result;
    }
    sampler.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    for (std::size_t slot = 3; slot < 5; ++slot)
    {
        result = device->CreateSamplerState(&sampler, &g_m13Samplers[slot]);
        if (FAILED(result))
            return result;
    }

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
    result = device->CreateBlendState(&blend, &g_m13BlendState);
    if (FAILED(result))
        return result;
    D3D11_DEPTH_STENCIL_DESC depth = {};
    depth.DepthEnable = FALSE;
    depth.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
    depth.DepthFunc = D3D11_COMPARISON_ALWAYS;
    result = device->CreateDepthStencilState(&depth, &g_m13DepthState);
    if (FAILED(result))
        return result;
    D3D11_RASTERIZER_DESC rasterizer = {};
    rasterizer.FillMode = D3D11_FILL_SOLID;
    rasterizer.CullMode = D3D11_CULL_NONE;
    rasterizer.DepthClipEnable = TRUE;
    return device->CreateRasterizerState(&rasterizer, &g_m13RasterizerState);
}

void ReleaseOpeningStripResources()
{
    g_openingStripScreenSizePatched.store(0, std::memory_order_release);
    g_openingStripResourceWidth = 0;
    g_openingStripResourceHeight = 0;
    ReleaseM14Object(g_openingStripRasterizerState);
    ReleaseM14Object(g_openingStripDepthState);
    ReleaseM14Object(g_openingStripBlendState);
    for (ID3D11SamplerState*& value : g_openingStripSamplers)
        ReleaseM14Object(value);
    ReleaseM14Object(g_openingStripMaskView);
    ReleaseM14Object(g_openingStripMaskTexture);
    ReleaseM14Object(g_openingStripSkinView);
    ReleaseM14Object(g_openingStripSkinBuffer);
    for (auto& packet : g_openingStripPixelConstantBuffers)
        for (ID3D11Buffer*& value : packet) ReleaseM14Object(value);
    for (auto& packet : g_openingStripVertexConstantBuffers)
        for (ID3D11Buffer*& value : packet) ReleaseM14Object(value);
    for (ID3D11Buffer*& value : g_openingStripIndexBuffers)
        ReleaseM14Object(value);
    for (ID3D11Buffer*& value : g_openingStripVertexBuffers)
        ReleaseM14Object(value);
    ReleaseM14Object(g_openingStripDefaultVertexBuffer);
    ReleaseM14Object(g_openingStripInputLayout);
    ReleaseM14Object(g_openingStripPixelShader);
    ReleaseM14Object(g_openingStripVertexShader);
}

HRESULT CreateOpeningStripResources(ID3D11Device* device)
{
    if (device == nullptr)
        return E_POINTER;
    std::uint32_t outputWidth = 0;
    std::uint32_t outputHeight = 0;
    UnpackOpeningStripDimensions(
        g_openingStripOutputDimensions.load(std::memory_order_acquire),
        outputWidth,
        outputHeight);
    if (outputWidth == 0 || outputHeight == 0 ||
        outputWidth > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION ||
        outputHeight > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION)
        return E_INVALIDARG;
    if (g_openingStripVertexShader != nullptr &&
        g_openingStripPixelShader != nullptr &&
        g_openingStripResourceWidth == outputWidth &&
        g_openingStripResourceHeight == outputHeight &&
        g_openingStripScreenSizePatched.load(std::memory_order_acquire) == 1u)
        return S_OK;
    ReleaseOpeningStripResources();
    HRESULT result = device->CreateVertexShader(
        g_EndfieldOpeningStripVertexDxbc,
        g_EndfieldOpeningStripVertexDxbcSize,
        nullptr,
        &g_openingStripVertexShader);
    if (FAILED(result)) return result;
    result = device->CreatePixelShader(
        g_EndfieldOpeningStripPixelDxbc,
        g_EndfieldOpeningStripPixelDxbcSize,
        nullptr,
        &g_openingStripPixelShader);
    if (FAILED(result)) return result;
    const D3D11_INPUT_ELEMENT_DESC elements[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 0, 24,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 28,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 1, DXGI_FORMAT_R32G32_FLOAT, 0, 36,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 4, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDWEIGHTS", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 1, 16,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDINDICES", 0, DXGI_FORMAT_R8G8B8A8_UINT, 1, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
    };
    result = device->CreateInputLayout(
        elements, static_cast<UINT>(sizeof(elements) / sizeof(elements[0])),
        g_EndfieldOpeningStripVertexDxbc,
        g_EndfieldOpeningStripVertexDxbcSize,
        &g_openingStripInputLayout);
    if (FAILED(result)) return result;
    const unsigned char defaultVertex[20] = {};
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_VERTEX_BUFFER, defaultVertex,
        sizeof(defaultVertex), &g_openingStripDefaultVertexBuffer);
    if (FAILED(result)) return result;
    for (std::uint32_t packet = 0;
         packet < g_EndfieldOpeningStripPacketCount; ++packet)
    {
        const EndfieldOpeningStripPacket& source =
            g_EndfieldOpeningStripPackets[packet];
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_VERTEX_BUFFER, source.vertices,
            static_cast<UINT>(source.vertexBytes),
            &g_openingStripVertexBuffers[packet]);
        if (FAILED(result)) return result;
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_INDEX_BUFFER, source.indices,
            static_cast<UINT>(source.indexBytes),
            &g_openingStripIndexBuffers[packet]);
        if (FAILED(result)) return result;
        for (std::size_t slot = 0; slot < 5; ++slot)
        {
            result = CreateOpeningStripConstantBuffer(
                device, g_EndfieldOpeningStripVSCounts[slot],
                source.vs[slot], source.vsBytes[slot],
                slot == 2u, outputWidth, outputHeight,
                &g_openingStripVertexConstantBuffers[packet][slot]);
            if (FAILED(result)) return result;
        }
        for (std::size_t slot = 0; slot < 4; ++slot)
        {
            result = CreateOpeningStripConstantBuffer(
                device, g_EndfieldOpeningStripPSCounts[slot],
                source.ps[slot], source.psBytes[slot],
                slot == 1u, outputWidth, outputHeight,
                &g_openingStripPixelConstantBuffers[packet][slot]);
            if (FAILED(result)) return result;
        }
    }
    const float zeroSkin[4] = {};
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_SHADER_RESOURCE, zeroSkin, sizeof(zeroSkin),
        &g_openingStripSkinBuffer, D3D11_RESOURCE_MISC_BUFFER_STRUCTURED,
        sizeof(zeroSkin));
    if (FAILED(result)) return result;
    result = device->CreateShaderResourceView(
        g_openingStripSkinBuffer, nullptr, &g_openingStripSkinView);
    if (FAILED(result)) return result;
    D3D11_TEXTURE2D_DESC maskDescription = {};
    maskDescription.Width = g_EndfieldOpeningStripMaskWidth;
    maskDescription.Height = g_EndfieldOpeningStripMaskHeight;
    maskDescription.MipLevels = 1;
    maskDescription.ArraySize = 1;
    maskDescription.Format = DXGI_FORMAT_BC7_UNORM_SRGB;
    maskDescription.SampleDesc.Count = 1;
    maskDescription.Usage = D3D11_USAGE_IMMUTABLE;
    maskDescription.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA maskInitial = {};
    maskInitial.pSysMem = g_EndfieldOpeningStripMaskBc7;
    maskInitial.SysMemPitch =
        ((g_EndfieldOpeningStripMaskWidth + 3u) / 4u) * 16u;
    maskInitial.SysMemSlicePitch =
        static_cast<UINT>(g_EndfieldOpeningStripMaskBc7Size);
    result = device->CreateTexture2D(
        &maskDescription, &maskInitial, &g_openingStripMaskTexture);
    if (FAILED(result)) return result;
    result = device->CreateShaderResourceView(
        g_openingStripMaskTexture, nullptr, &g_openingStripMaskView);
    if (FAILED(result)) return result;
    D3D11_SAMPLER_DESC sampler = {};
    sampler.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    sampler.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.MaxLOD = 1000.0f;
    result = device->CreateSamplerState(&sampler, &g_openingStripSamplers[0]);
    if (FAILED(result)) return result;
    sampler.AddressU = D3D11_TEXTURE_ADDRESS_WRAP;
    sampler.AddressV = D3D11_TEXTURE_ADDRESS_WRAP;
    sampler.AddressW = D3D11_TEXTURE_ADDRESS_WRAP;
    result = device->CreateSamplerState(&sampler, &g_openingStripSamplers[1]);
    if (FAILED(result)) return result;
    D3D11_BLEND_DESC blend = {};
    blend.IndependentBlendEnable = TRUE;
    for (std::size_t target = 0; target < 2; ++target)
    {
        blend.RenderTarget[target].BlendEnable = TRUE;
        blend.RenderTarget[target].SrcBlend = D3D11_BLEND_SRC_ALPHA;
        blend.RenderTarget[target].DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
        blend.RenderTarget[target].BlendOp = D3D11_BLEND_OP_ADD;
        blend.RenderTarget[target].SrcBlendAlpha = D3D11_BLEND_ONE;
        blend.RenderTarget[target].DestBlendAlpha = D3D11_BLEND_ZERO;
        blend.RenderTarget[target].BlendOpAlpha = D3D11_BLEND_OP_ADD;
        blend.RenderTarget[target].RenderTargetWriteMask =
            D3D11_COLOR_WRITE_ENABLE_ALL;
    }
    result = device->CreateBlendState(&blend, &g_openingStripBlendState);
    if (FAILED(result)) return result;
    D3D11_DEPTH_STENCIL_DESC depth = {};
    depth.DepthEnable = TRUE;
    depth.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
    depth.DepthFunc = D3D11_COMPARISON_ALWAYS;
    result = device->CreateDepthStencilState(&depth, &g_openingStripDepthState);
    if (FAILED(result)) return result;
    D3D11_RASTERIZER_DESC rasterizer = {};
    rasterizer.FillMode = D3D11_FILL_SOLID;
    rasterizer.CullMode = D3D11_CULL_BACK;
    rasterizer.FrontCounterClockwise = TRUE;
    rasterizer.DepthClipEnable = TRUE;
    rasterizer.ScissorEnable = TRUE;
    result = device->CreateRasterizerState(
        &rasterizer, &g_openingStripRasterizerState);
    if (FAILED(result)) return result;
    g_openingStripResourceWidth = outputWidth;
    g_openingStripResourceHeight = outputHeight;
    g_openingStripScreenSizePatched.store(1u, std::memory_order_release);
    return S_OK;
}

void ReleaseM27DrawResources()
{
    ReleaseM14Object(g_m27DrawRasterizerState);
    ReleaseM14Object(g_m27DrawDepthState);
    ReleaseM14Object(g_m27DrawBlendState);
    ReleaseM14Object(g_m27DrawSampler);
    for (ID3D11ShaderResourceView*& view : g_m27DrawTextureViews)
        ReleaseM14Object(view);
    for (ID3D11Texture2D*& texture : g_m27DrawTextures)
        ReleaseM14Object(texture);
    ReleaseM14Object(g_m27DrawSkinView);
    ReleaseM14Object(g_m27DrawSkinBuffer);
    for (std::uint32_t frame = 0; frame < g_EndfieldM27TemporalFrameCount; ++frame)
    {
        for (std::uint32_t draw = 0; draw < kM27MaximumDrawsPerFrame; ++draw)
        {
            for (ID3D11Buffer*& buffer : g_m27DrawPixelConstantBuffers[frame][draw])
                ReleaseM14Object(buffer);
            for (ID3D11Buffer*& buffer : g_m27DrawVertexConstantBuffers[frame][draw])
                ReleaseM14Object(buffer);
            ReleaseM14Object(g_m27DrawIndexBuffers[frame][draw]);
            ReleaseM14Object(g_m27DrawVertexBuffers[frame][draw]);
        }
    }
    ReleaseM14Object(g_m27DrawDefaultVertexBuffer);
    for (ID3D11InputLayout*& layout : g_m27DrawInputLayouts)
        ReleaseM14Object(layout);
    ReleaseM14Object(g_m27DrawPixelShader);
    ReleaseM14Object(g_m27DrawVertexShader);
}

HRESULT CreateM27Texture(
    ID3D11Device* device,
    const EndfieldM27TemporalTexturePayload& payload,
    ID3D11Texture2D** texture,
    ID3D11ShaderResourceView** view)
{
    if (device == nullptr || payload.data == nullptr || payload.bytes == 0 ||
        payload.width == 0 || payload.height == 0 || texture == nullptr ||
        view == nullptr)
        return E_INVALIDARG;
    const DXGI_FORMAT format = static_cast<DXGI_FORMAT>(payload.format);
    UINT rowPitch = 0;
    if (format == DXGI_FORMAT_BC5_UNORM ||
        format == DXGI_FORMAT_BC7_UNORM ||
        format == DXGI_FORMAT_BC7_UNORM_SRGB)
        rowPitch = ((payload.width + 3u) / 4u) * 16u;
    else if (format == DXGI_FORMAT_R8G8B8A8_UNORM_SRGB)
        rowPitch = payload.width * 4u;
    else
        return E_INVALIDARG;
    D3D11_TEXTURE2D_DESC description = {};
    description.Width = payload.width;
    description.Height = payload.height;
    description.MipLevels = 1;
    description.ArraySize = 1;
    description.Format = format;
    description.SampleDesc.Count = 1;
    description.Usage = D3D11_USAGE_IMMUTABLE;
    description.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA initial = {};
    initial.pSysMem = payload.data;
    initial.SysMemPitch = rowPitch;
    initial.SysMemSlicePitch = static_cast<UINT>(payload.bytes);
    HRESULT result = device->CreateTexture2D(&description, &initial, texture);
    if (FAILED(result))
        return result;
    result = device->CreateShaderResourceView(*texture, nullptr, view);
    if (FAILED(result))
        ReleaseM14Object(*texture);
    return result;
}

HRESULT CreateM27DrawResources(ID3D11Device* device)
{
    if (device == nullptr)
        return E_POINTER;
    if (g_m27DrawVertexShader != nullptr && g_m27DrawPixelShader != nullptr)
        return S_OK;
    ReleaseM27DrawResources();

    g_m27DrawFailureStage.store(101u, std::memory_order_relaxed);
    HRESULT result = device->CreateVertexShader(
        g_EndfieldM27VertexDxbc,
        g_EndfieldM27VertexDxbcSize,
        nullptr,
        &g_m27DrawVertexShader);
    if (FAILED(result))
        return result;
    g_m27DrawFailureStage.store(102u, std::memory_order_relaxed);
    result = device->CreatePixelShader(
        g_EndfieldM27PixelDxbc,
        g_EndfieldM27PixelDxbcSize,
        nullptr,
        &g_m27DrawPixelShader);
    if (FAILED(result))
        return result;

    const D3D11_INPUT_ELEMENT_DESC elements60[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"NORMAL", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 12,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TANGENT", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 1, 12,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 0, 24,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 28,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 1, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 4, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDWEIGHTS", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 1, 16,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDINDICES", 0, DXGI_FORMAT_R8G8B8A8_UINT, 1, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
    };
    g_m27DrawFailureStage.store(103u, std::memory_order_relaxed);
    result = device->CreateInputLayout(
        elements60,
        static_cast<UINT>(sizeof(elements60) / sizeof(elements60[0])),
        g_EndfieldM27VertexDxbc,
        g_EndfieldM27VertexDxbcSize,
        &g_m27DrawInputLayouts[0]);
    if (FAILED(result))
        return result;
    const D3D11_INPUT_ELEMENT_DESC elements68[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"NORMAL", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 12,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TANGENT", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 24,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 0, 40,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 1, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 52,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 4, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 52,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDWEIGHTS", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 1, 16,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDINDICES", 0, DXGI_FORMAT_R8G8B8A8_UINT, 1, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
    };
    g_m27DrawFailureStage.store(104u, std::memory_order_relaxed);
    result = device->CreateInputLayout(
        elements68,
        static_cast<UINT>(sizeof(elements68) / sizeof(elements68[0])),
        g_EndfieldM27VertexDxbc,
        g_EndfieldM27VertexDxbcSize,
        &g_m27DrawInputLayouts[1]);
    if (FAILED(result))
        return result;

    g_m27DrawFailureStage.store(105u, std::memory_order_relaxed);
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_VERTEX_BUFFER, g_EndfieldM27TemporalDefaultVertex,
        static_cast<UINT>(g_EndfieldM27TemporalDefaultVertexSize),
        &g_m27DrawDefaultVertexBuffer);
    if (FAILED(result))
        return result;
    for (std::uint32_t frame = 0; frame < g_EndfieldM27TemporalFrameCount; ++frame)
    {
        const EndfieldM27TemporalFramePayload& packet =
            g_EndfieldM27TemporalFrames[frame];
        if (packet.drawCount > kM27MaximumDrawsPerFrame)
            return E_INVALIDARG;
        for (std::uint32_t draw = 0; draw < packet.drawCount; ++draw)
        {
            const EndfieldM27TemporalDrawPayload& payload = packet.draws[draw];
            const std::uint32_t drawStage = 1000u + frame * 100u + draw * 10u;
            g_m27DrawFailureStage.store(drawStage + 1u, std::memory_order_relaxed);
            result = CreateM14ImmutableBuffer(
                device, D3D11_BIND_VERTEX_BUFFER, payload.vertices,
                static_cast<UINT>(payload.vertexBytes),
                &g_m27DrawVertexBuffers[frame][draw]);
            if (FAILED(result)) return result;
            g_m27DrawFailureStage.store(drawStage + 2u, std::memory_order_relaxed);
            result = CreateM14ImmutableBuffer(
                device, D3D11_BIND_INDEX_BUFFER, payload.indices,
                static_cast<UINT>(payload.indexBytes),
                &g_m27DrawIndexBuffers[frame][draw]);
            if (FAILED(result)) return result;
            for (std::size_t slot = 0; slot < 3; ++slot)
            {
                g_m27DrawFailureStage.store(
                    drawStage + 3u + static_cast<std::uint32_t>(slot),
                    std::memory_order_relaxed);
                result = CreateM14ConstantBuffer(
                    device, g_EndfieldM27TemporalVSDeclaredFloat4Counts[slot],
                    payload.vs[slot], payload.vsBytes[slot],
                    &g_m27DrawVertexConstantBuffers[frame][draw][slot]);
                if (FAILED(result)) return result;
            }
            for (std::size_t slot = 0; slot < 5; ++slot)
            {
                g_m27DrawFailureStage.store(
                    drawStage + 6u + static_cast<std::uint32_t>(slot),
                    std::memory_order_relaxed);
                result = CreateM14ConstantBuffer(
                    device, g_EndfieldM27TemporalPSDeclaredFloat4Counts[slot],
                    payload.ps[slot], payload.psBytes[slot],
                    &g_m27DrawPixelConstantBuffers[frame][draw][slot]);
                if (FAILED(result)) return result;
            }
        }
    }
    const float zeroSkin[4] = {};
    g_m27DrawFailureStage.store(2001u, std::memory_order_relaxed);
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_SHADER_RESOURCE, zeroSkin, sizeof(zeroSkin),
        &g_m27DrawSkinBuffer, D3D11_RESOURCE_MISC_BUFFER_STRUCTURED,
        sizeof(zeroSkin));
    if (FAILED(result))
        return result;

    for (std::size_t slot = 0; slot < 6; ++slot)
    {
        g_m27DrawFailureStage.store(
            2010u + static_cast<std::uint32_t>(slot),
            std::memory_order_relaxed);
        result = CreateM27Texture(
            device, g_EndfieldM27TemporalTextures[slot],
            &g_m27DrawTextures[slot], &g_m27DrawTextureViews[slot]);
        if (FAILED(result))
            return result;
    }
    g_m27DrawFailureStage.store(2020u, std::memory_order_relaxed);
    result = device->CreateShaderResourceView(
        g_m27DrawSkinBuffer, nullptr, &g_m27DrawSkinView);
    if (FAILED(result))
        return result;

    D3D11_SAMPLER_DESC sampler = {};
    sampler.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    sampler.AddressU = D3D11_TEXTURE_ADDRESS_WRAP;
    sampler.AddressV = D3D11_TEXTURE_ADDRESS_WRAP;
    sampler.AddressW = D3D11_TEXTURE_ADDRESS_WRAP;
    sampler.MaxLOD = D3D11_FLOAT32_MAX;
    g_m27DrawFailureStage.store(2021u, std::memory_order_relaxed);
    result = device->CreateSamplerState(&sampler, &g_m27DrawSampler);
    if (FAILED(result))
        return result;

    D3D11_BLEND_DESC blend = {};
    blend.IndependentBlendEnable = TRUE;
    for (std::size_t target = 0; target < 5; ++target)
        blend.RenderTarget[target].RenderTargetWriteMask =
            D3D11_COLOR_WRITE_ENABLE_ALL;
    g_m27DrawFailureStage.store(2022u, std::memory_order_relaxed);
    result = device->CreateBlendState(&blend, &g_m27DrawBlendState);
    if (FAILED(result))
        return result;

    D3D11_DEPTH_STENCIL_DESC depth = {};
    depth.DepthEnable = TRUE;
    depth.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ALL;
    depth.DepthFunc = D3D11_COMPARISON_ALWAYS;
    depth.StencilEnable = TRUE;
    depth.StencilReadMask = D3D11_DEFAULT_STENCIL_READ_MASK;
    depth.StencilWriteMask = D3D11_DEFAULT_STENCIL_WRITE_MASK;
    depth.FrontFace.StencilFailOp = D3D11_STENCIL_OP_KEEP;
    depth.FrontFace.StencilDepthFailOp = D3D11_STENCIL_OP_KEEP;
    depth.FrontFace.StencilPassOp = D3D11_STENCIL_OP_REPLACE;
    depth.FrontFace.StencilFunc = D3D11_COMPARISON_ALWAYS;
    depth.BackFace = depth.FrontFace;
    g_m27DrawFailureStage.store(2023u, std::memory_order_relaxed);
    result = device->CreateDepthStencilState(&depth, &g_m27DrawDepthState);
    if (FAILED(result))
        return result;

    D3D11_RASTERIZER_DESC rasterizer = {};
    rasterizer.FillMode = D3D11_FILL_SOLID;
    rasterizer.CullMode = D3D11_CULL_NONE;
    rasterizer.DepthClipEnable = TRUE;
    g_m27DrawFailureStage.store(2024u, std::memory_order_relaxed);
    result = device->CreateRasterizerState(
        &rasterizer, &g_m27DrawRasterizerState);
    if (SUCCEEDED(result))
        g_m27DrawFailureStage.store(0u, std::memory_order_relaxed);
    return result;
}

void ReleaseM29RuntimeResources()
{
    ReleaseM14Object(g_m29RasterizerState);
    ReleaseM14Object(g_m29DepthState);
    ReleaseM14Object(g_m29BlendState);
    for (ID3D11SamplerState*& sampler : g_m29Samplers)
        ReleaseM14Object(sampler);
    for (ID3D11ShaderResourceView*& view : g_m29TextureViews)
        ReleaseM14Object(view);
    for (ID3D11Texture2D*& texture : g_m29Textures)
        ReleaseM14Object(texture);
    ReleaseM14Object(g_m29SkinView);
    ReleaseM14Object(g_m29SkinBuffer);
    for (std::uint32_t packet = 0;
         packet < g_EndfieldM29PacketCount; ++packet)
    {
        for (ID3D11Buffer*& buffer : g_m29PixelConstantBuffers[packet])
            ReleaseM14Object(buffer);
        for (ID3D11Buffer*& buffer : g_m29VertexConstantBuffers[packet])
            ReleaseM14Object(buffer);
        ReleaseM14Object(g_m29IndexBuffers[packet]);
        ReleaseM14Object(g_m29SecondaryBuffers[packet]);
        ReleaseM14Object(g_m29VertexBuffers[packet]);
    }
    for (ID3D11InputLayout*& layout : g_m29InputLayouts)
        ReleaseM14Object(layout);
    ReleaseM14Object(g_m29RuntimePixelShader);
    ReleaseM14Object(g_m29RuntimeVertexShader);
}

HRESULT CreateM29Texture(
    ID3D11Device* device,
    const std::uint8_t* data,
    std::size_t bytes,
    UINT width,
    UINT height,
    ID3D11Texture2D** texture,
    ID3D11ShaderResourceView** view)
{
    if (device == nullptr || data == nullptr || bytes == 0 || width == 0 ||
        height == 0 || texture == nullptr || view == nullptr)
        return E_INVALIDARG;
    const UINT rowPitch = ((width + 3u) / 4u) * 16u;
    const std::size_t requiredBytes =
        static_cast<std::size_t>(rowPitch) * ((height + 3u) / 4u);
    if (bytes != requiredBytes || bytes > UINT_MAX)
        return E_INVALIDARG;

    D3D11_TEXTURE2D_DESC description = {};
    description.Width = width;
    description.Height = height;
    description.MipLevels = 1;
    description.ArraySize = 1;
    description.Format =
        static_cast<DXGI_FORMAT>(g_EndfieldM29TextureFormat);
    if (description.Format != DXGI_FORMAT_BC7_UNORM_SRGB)
        return E_INVALIDARG;
    description.SampleDesc.Count = 1;
    description.Usage = D3D11_USAGE_IMMUTABLE;
    description.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA initial = {};
    initial.pSysMem = data;
    initial.SysMemPitch = rowPitch;
    initial.SysMemSlicePitch = static_cast<UINT>(bytes);
    HRESULT result = device->CreateTexture2D(&description, &initial, texture);
    if (FAILED(result))
        return result;
    result = device->CreateShaderResourceView(*texture, nullptr, view);
    if (FAILED(result))
        ReleaseM14Object(*texture);
    return result;
}

HRESULT CreateM29RuntimeResources(ID3D11Device* device)
{
    if (device == nullptr)
        return E_POINTER;
    if (g_m29RuntimeVertexShader != nullptr &&
        g_m29RuntimePixelShader != nullptr)
        return S_OK;
    ReleaseM29RuntimeResources();

    HRESULT result = device->CreateVertexShader(
        g_EndfieldM29VertexShaderBytecode,
        g_EndfieldM29VertexShaderBytecodeSize,
        nullptr,
        &g_m29RuntimeVertexShader);
    if (FAILED(result))
        return result;
    result = device->CreatePixelShader(
        g_EndfieldM29PixelShaderBytecode,
        g_EndfieldM29PixelShaderBytecodeSize,
        nullptr,
        &g_m29RuntimePixelShader);
    if (FAILED(result))
        return result;

    const D3D11_INPUT_ELEMENT_DESC elements60[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"NORMAL", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 12,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TANGENT", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 1, 12,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 0, 24,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 28,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 1, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 4, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDWEIGHTS", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 1, 16,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDINDICES", 0, DXGI_FORMAT_R8G8B8A8_UINT, 1, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
    };
    result = device->CreateInputLayout(
        elements60,
        static_cast<UINT>(sizeof(elements60) / sizeof(elements60[0])),
        g_EndfieldM29VertexShaderBytecode,
        g_EndfieldM29VertexShaderBytecodeSize,
        &g_m29InputLayouts[0]);
    if (FAILED(result))
        return result;

    const D3D11_INPUT_ELEMENT_DESC elements68[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"NORMAL", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 12,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TANGENT", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 24,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 0, 40,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 44,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 1, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 52,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 4, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 52,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDWEIGHTS", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 1, 16,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDINDICES", 0, DXGI_FORMAT_R8G8B8A8_UINT, 1, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
    };
    result = device->CreateInputLayout(
        elements68,
        static_cast<UINT>(sizeof(elements68) / sizeof(elements68[0])),
        g_EndfieldM29VertexShaderBytecode,
        g_EndfieldM29VertexShaderBytecodeSize,
        &g_m29InputLayouts[1]);
    if (FAILED(result))
        return result;

    for (std::uint32_t packetIndex = 0;
         packetIndex < g_EndfieldM29PacketCount; ++packetIndex)
    {
        const EndfieldM29PacketPayload& packet =
            g_EndfieldM29Packets[packetIndex];
        if (packet.vertexStride != 60u && packet.vertexStride != 68u)
            return E_INVALIDARG;
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_VERTEX_BUFFER, packet.vertices,
            static_cast<UINT>(packet.vertexBytes),
            &g_m29VertexBuffers[packetIndex]);
        if (FAILED(result)) return result;
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_VERTEX_BUFFER, packet.secondary,
            static_cast<UINT>(packet.secondaryBytes),
            &g_m29SecondaryBuffers[packetIndex]);
        if (FAILED(result)) return result;
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_INDEX_BUFFER, packet.indices,
            static_cast<UINT>(packet.indexBytes),
            &g_m29IndexBuffers[packetIndex]);
        if (FAILED(result)) return result;
        for (std::size_t slot = 0; slot < kM29VSConstantBufferCount; ++slot)
        {
            result = CreateM14ConstantBuffer(
                device, g_EndfieldM29VSDeclaredFloat4Counts[slot],
                packet.vs[slot], packet.vsBytes[slot],
                &g_m29VertexConstantBuffers[packetIndex][slot]);
            if (FAILED(result)) return result;
        }
        for (std::size_t slot = 0; slot < kM29PSConstantBufferCount; ++slot)
        {
            result = CreateM14ConstantBuffer(
                device, g_EndfieldM29PSDeclaredFloat4Counts[slot],
                packet.ps[slot], packet.psBytes[slot],
                &g_m29PixelConstantBuffers[packetIndex][slot]);
            if (FAILED(result)) return result;
        }
    }

    const float zeroSkin[4] = {};
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_SHADER_RESOURCE, zeroSkin, sizeof(zeroSkin),
        &g_m29SkinBuffer, D3D11_RESOURCE_MISC_BUFFER_STRUCTURED,
        sizeof(zeroSkin));
    if (FAILED(result))
        return result;
    result = device->CreateShaderResourceView(
        g_m29SkinBuffer, nullptr, &g_m29SkinView);
    if (FAILED(result))
        return result;

    result = CreateM29Texture(
        device, g_EndfieldM29TextureT0, g_EndfieldM29TextureT0Size,
        g_EndfieldM29TextureT0Width, g_EndfieldM29TextureT0Height,
        &g_m29Textures[0], &g_m29TextureViews[0]);
    if (FAILED(result))
        return result;
    result = CreateM29Texture(
        device, g_EndfieldM29TextureT1, g_EndfieldM29TextureT1Size,
        g_EndfieldM29TextureT1Width, g_EndfieldM29TextureT1Height,
        &g_m29Textures[1], &g_m29TextureViews[1]);
    if (FAILED(result))
        return result;

    D3D11_SAMPLER_DESC sampler = {};
    // Frame 2723 records numeric filter 20: linear min/mag with point mip.
    sampler.Filter = D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT;
    sampler.AddressU = D3D11_TEXTURE_ADDRESS_WRAP;
    sampler.AddressV = D3D11_TEXTURE_ADDRESS_WRAP;
    sampler.AddressW = D3D11_TEXTURE_ADDRESS_WRAP;
    sampler.MaxLOD = 1000.0f;
    for (ID3D11SamplerState*& state : g_m29Samplers)
    {
        result = device->CreateSamplerState(&sampler, &state);
        if (FAILED(result))
            return result;
    }

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
    result = device->CreateBlendState(&blend, &g_m29BlendState);
    if (FAILED(result))
        return result;

    D3D11_DEPTH_STENCIL_DESC depth = {};
    depth.DepthEnable = TRUE;
    depth.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
    depth.DepthFunc = D3D11_COMPARISON_ALWAYS;
    depth.StencilEnable = TRUE;
    depth.StencilReadMask = D3D11_DEFAULT_STENCIL_READ_MASK;
    depth.StencilWriteMask = D3D11_DEFAULT_STENCIL_WRITE_MASK;
    depth.FrontFace.StencilFailOp = D3D11_STENCIL_OP_KEEP;
    depth.FrontFace.StencilDepthFailOp = D3D11_STENCIL_OP_KEEP;
    depth.FrontFace.StencilPassOp = D3D11_STENCIL_OP_KEEP;
    depth.FrontFace.StencilFunc = D3D11_COMPARISON_ALWAYS;
    depth.BackFace = depth.FrontFace;
    result = device->CreateDepthStencilState(&depth, &g_m29DepthState);
    if (FAILED(result))
        return result;

    D3D11_RASTERIZER_DESC rasterizer = {};
    rasterizer.FillMode = D3D11_FILL_SOLID;
    rasterizer.CullMode = D3D11_CULL_NONE;
    rasterizer.FrontCounterClockwise = TRUE;
    rasterizer.DepthClipEnable = TRUE;
    rasterizer.ScissorEnable = TRUE;
    return device->CreateRasterizerState(
        &rasterizer, &g_m29RasterizerState);
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

HRESULT CreateM31ReadOnlyDepthStencilView(
    ID3D11Device* device,
    ID3D11Resource* resource,
    ID3D11DepthStencilView** view)
{
    if (device == nullptr || resource == nullptr || view == nullptr)
        return E_POINTER;
    *view = nullptr;
    ID3D11Texture2D* texture = nullptr;
    HRESULT result = resource->QueryInterface(
        __uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&texture));
    if (FAILED(result) || texture == nullptr)
        return FAILED(result) ? result : E_NOINTERFACE;
    D3D11_TEXTURE2D_DESC textureDescription = {};
    texture->GetDesc(&textureDescription);
    texture->Release();
    if (textureDescription.Format != DXGI_FORMAT_R32G8X24_TYPELESS ||
        textureDescription.ArraySize != 1u ||
        textureDescription.SampleDesc.Count != 1u ||
        (textureDescription.BindFlags & D3D11_BIND_DEPTH_STENCIL) == 0u)
        return E_INVALIDARG;
    D3D11_DEPTH_STENCIL_VIEW_DESC description =
        EndfieldM31FixedState::ReadOnlyDepthView();
    return device->CreateDepthStencilView(resource, &description, view);
}

bool ValidateM31OutputCompatibility(
    ID3D11RenderTargetView* const renderTargets[2],
    ID3D11Resource* depthResource)
{
    if (renderTargets == nullptr || renderTargets[0] == nullptr ||
        renderTargets[1] == nullptr || depthResource == nullptr)
        return false;

    D3D11_TEXTURE2D_DESC descriptions[3] = {};
    for (UINT target = 0u; target < 2u; ++target)
    {
        D3D11_RENDER_TARGET_VIEW_DESC viewDescription = {};
        renderTargets[target]->GetDesc(&viewDescription);
        if (viewDescription.ViewDimension != D3D11_RTV_DIMENSION_TEXTURE2D)
            return false;
        ID3D11Resource* resource = nullptr;
        ID3D11Texture2D* texture = nullptr;
        renderTargets[target]->GetResource(&resource);
        const HRESULT result = resource == nullptr ? E_POINTER :
            resource->QueryInterface(
                __uuidof(ID3D11Texture2D),
                reinterpret_cast<void**>(&texture));
        ReleaseM14Object(resource);
        if (FAILED(result) || texture == nullptr)
        {
            ReleaseM14Object(texture);
            return false;
        }
        texture->GetDesc(&descriptions[target]);
        ReleaseM14Object(texture);
    }
    ID3D11Texture2D* depthTexture = nullptr;
    const HRESULT depthResult = depthResource->QueryInterface(
        __uuidof(ID3D11Texture2D),
        reinterpret_cast<void**>(&depthTexture));
    if (FAILED(depthResult) || depthTexture == nullptr)
    {
        ReleaseM14Object(depthTexture);
        return false;
    }
    depthTexture->GetDesc(&descriptions[2]);
    ReleaseM14Object(depthTexture);

    for (UINT index = 0u; index < 3u; ++index)
    {
        const D3D11_TEXTURE2D_DESC& row = descriptions[index];
        if (row.Width == 0u || row.Height == 0u || row.ArraySize != 1u ||
            row.SampleDesc.Count != 1u)
            return false;
        if (index > 0u &&
            (row.Width != descriptions[0].Width ||
             row.Height != descriptions[0].Height ||
             row.SampleDesc.Count != descriptions[0].SampleDesc.Count ||
             row.SampleDesc.Quality != descriptions[0].SampleDesc.Quality))
            return false;
    }
    return true;
}

bool ValidateM31BoundState(
    ID3D11DeviceContext* context,
    ID3D11RenderTargetView* const expectedTargets[2],
    ID3D11DepthStencilView* expectedDepth,
    ID3D11ShaderResourceView* const expectedViews[2])
{
    if (context == nullptr || expectedTargets == nullptr ||
        expectedDepth == nullptr || expectedViews == nullptr)
        return false;

    ID3D11RenderTargetView* targets[2] = {};
    ID3D11DepthStencilView* depth = nullptr;
    ID3D11ShaderResourceView* views[2] = {};
    ID3D11SamplerState* samplers[2] = {};
    ID3D11BlendState* blend = nullptr;
    ID3D11DepthStencilState* depthState = nullptr;
    ID3D11RasterizerState* rasterizer = nullptr;
    FLOAT factor[4] = {};
    UINT sampleMask = 0u;
    UINT stencilReference = ~0u;
    context->OMGetRenderTargets(2, targets, &depth);
    context->PSGetShaderResources(0, 2, views);
    context->PSGetSamplers(0, 2, samplers);
    context->OMGetBlendState(&blend, factor, &sampleMask);
    context->OMGetDepthStencilState(&depthState, &stencilReference);
    context->RSGetState(&rasterizer);
    bool valid = targets[0] == expectedTargets[0] &&
        targets[1] == expectedTargets[1] && depth == expectedDepth &&
        views[0] == expectedViews[0] && views[1] == expectedViews[1] &&
        samplers[0] == g_m31PeakSamplers[0] &&
        samplers[1] == g_m31PeakSamplers[1] &&
        blend == g_m31PeakBlendState && depthState == g_m31PeakDepthState &&
        rasterizer == g_m31PeakRasterizerState &&
        factor[0] == 1.0f && factor[1] == 1.0f &&
        factor[2] == 1.0f && factor[3] == 1.0f &&
        sampleMask == 0xffffffffu && stencilReference == 0u;
    ReleaseM14Object(rasterizer);
    ReleaseM14Object(depthState);
    ReleaseM14Object(blend);
    for (ID3D11SamplerState*& value : samplers)
        ReleaseM14Object(value);
    for (ID3D11ShaderResourceView*& value : views)
        ReleaseM14Object(value);
    ReleaseM14Object(depth);
    for (ID3D11RenderTargetView*& value : targets)
        ReleaseM14Object(value);
    return valid;
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
    // Event 3 is the runtime-only arm edge. Shader-compilation probes may
    // have left the mutually exclusive M27 route selected or reset the route
    // to None; DrawExactRuntimeShader must see the deferred route explicitly.
    g_substitutionRoute.store(
        SubstitutionRoute::DeferredDiagnostic,
        std::memory_order_release);
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
            g_substitutionRoute.store(
                SubstitutionRoute::None,
                std::memory_order_release);
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
    if (SUCCEEDED(result))
        result = EnsureM14ScreenConstantBuffers(device);
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
    UINT oldViewportCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_VIEWPORT oldViewports[
        D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    UINT oldScissorCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_RECT oldScissors[
        D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};

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
    context->RSGetViewports(&oldViewportCount, oldViewports);
    context->RSGetScissorRects(&oldScissorCount, oldScissors);

    const std::uint32_t packetIndex =
        g_m14PacketIndex.load(std::memory_order_acquire);
    if (packetIndex >= g_EndfieldM14PacketCount)
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
    const EndfieldM14PacketPayload& packet = g_EndfieldM14Packets[packetIndex];
    ID3D11Buffer* vertexBuffers[2] = {
        g_m14VertexBuffers[packetIndex],
        g_m14DefaultVertexBuffer,
    };
    const UINT strides[2] = {g_EndfieldM14VertexStride, 0};
    const UINT offsets[2] = {};
    const FLOAT blendFactor[4] = {};
    context->IASetInputLayout(g_m14InputLayout);
    context->IASetVertexBuffers(0, 2, vertexBuffers, strides, offsets);
    context->IASetIndexBuffer(
        g_m14IndexBuffers[packetIndex], DXGI_FORMAT_R16_UINT, 0);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_m14RuntimeVertexShader, nullptr, 0);
    context->PSSetShader(g_m14RuntimePixelShader, nullptr, 0);
    context->VSSetConstantBuffers(
        0, 5, g_m14VertexConstantBuffers[packetIndex]);
    context->PSSetConstantBuffers(
        0, 4, g_m14PixelConstantBuffers[packetIndex]);
    context->VSSetShaderResources(0, 1, &g_m14SkinView);
    context->PSSetShaderResources(0, 2, m14PixelViews);
    context->PSSetSamplers(0, 2, g_m14Samplers);
    context->OMSetBlendState(g_m14BlendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(g_m14DepthState, 0);
    context->RSSetState(g_m14RasterizerState);
    const D3D11_VIEWPORT viewport = {
        0.0f, 0.0f, static_cast<float>(g_m14ResourceWidth),
        static_cast<float>(g_m14ResourceHeight), 0.0f, 1.0f};
    const D3D11_RECT scissor = {
        0, 0, static_cast<LONG>(g_m14ResourceWidth),
        static_cast<LONG>(g_m14ResourceHeight)};
    context->RSSetViewports(1, &viewport);
    context->RSSetScissorRects(1, &scissor);
    context->DrawIndexed(packet.indexCount, 0, 0);

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
    context->RSSetViewports(oldViewportCount, oldViewports);
    context->RSSetScissorRects(oldScissorCount, oldScissors);

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

void UNITY_INTERFACE_API DrawM18PeakExactRuntime(int eventId)
{
    if (eventId != 0)
        return;
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_m18PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m18PeakLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    HRESULT result = CreateM14RuntimeResources(device);
    if (FAILED(result))
    {
        ReleaseM14RuntimeResources();
        g_m18PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m18PeakLastResult.store(result, std::memory_order_relaxed);
        return;
    }
    result = EnsureM18ScreenConstantBuffers(device);
    if (FAILED(result))
    {
        g_m18PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m18PeakLastResult.store(result, std::memory_order_relaxed);
        return;
    }
    ID3D11ShaderResourceView* textureViews[5] = {};
    for (std::size_t slot = 0; slot < 5; ++slot)
    {
        ID3D11Resource* resource = reinterpret_cast<ID3D11Resource*>(
            g_m18PeakTextures[slot].load(std::memory_order_acquire));
        result = CreateDiagnosticShaderResourceView(
            device, resource, &textureViews[slot]);
        if (FAILED(result) || textureViews[slot] == nullptr)
        {
            for (ID3D11ShaderResourceView*& view : textureViews)
                ReleaseM14Object(view);
            g_m18PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
            g_m18PeakLastResult.store(
                FAILED(result) ? result : E_POINTER, std::memory_order_relaxed);
            return;
        }
    }
    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        for (ID3D11ShaderResourceView*& view : textureViews)
            ReleaseM14Object(view);
        g_m18PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m18PeakLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    ID3D11RenderTargetView* renderTarget = nullptr;
    ID3D11DepthStencilView* renderDepth = nullptr;
    context->OMGetRenderTargets(1, &renderTarget, &renderDepth);
    if (renderTarget == nullptr || renderDepth == nullptr ||
        g_m14SkinView == nullptr)
    {
        ReleaseM14Object(renderDepth);
        ReleaseM14Object(renderTarget);
        context->Release();
        for (ID3D11ShaderResourceView*& view : textureViews)
            ReleaseM14Object(view);
        g_m18PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m18PeakLastResult.store(E_INVALIDARG, std::memory_order_relaxed);
        return;
    }

    ID3D11VertexShader* oldVS = nullptr;
    ID3D11PixelShader* oldPS = nullptr;
    ID3D11InputLayout* oldLayout = nullptr;
    ID3D11Buffer* oldVBs[2] = {};
    ID3D11Buffer* oldIB = nullptr;
    ID3D11Buffer* oldVSCBs[5] = {};
    ID3D11Buffer* oldPSCBs[4] = {};
    ID3D11ShaderResourceView* oldVSView = nullptr;
    ID3D11ShaderResourceView* oldPSViews[5] = {};
    ID3D11SamplerState* oldSamplers[5] = {};
    ID3D11BlendState* oldBlend = nullptr;
    ID3D11DepthStencilState* oldDepth = nullptr;
    ID3D11RasterizerState* oldRasterizer = nullptr;
    D3D11_PRIMITIVE_TOPOLOGY oldTopology = D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    DXGI_FORMAT oldIndexFormat = DXGI_FORMAT_UNKNOWN;
    UINT oldStrides[2] = {};
    UINT oldOffsets[2] = {};
    UINT oldIndexOffset = 0;
    FLOAT oldBlendFactor[4] = {};
    UINT oldSampleMask = 0;
    UINT oldStencilReference = 0;
    UINT oldViewportCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_VIEWPORT oldViewports[
        D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    UINT oldScissorCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_RECT oldScissors[
        D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    context->VSGetShader(&oldVS, nullptr, nullptr);
    context->PSGetShader(&oldPS, nullptr, nullptr);
    context->IAGetInputLayout(&oldLayout);
    context->IAGetVertexBuffers(0, 2, oldVBs, oldStrides, oldOffsets);
    context->IAGetIndexBuffer(&oldIB, &oldIndexFormat, &oldIndexOffset);
    context->IAGetPrimitiveTopology(&oldTopology);
    context->VSGetConstantBuffers(0, 5, oldVSCBs);
    context->PSGetConstantBuffers(0, 4, oldPSCBs);
    context->VSGetShaderResources(0, 1, &oldVSView);
    context->PSGetShaderResources(0, 5, oldPSViews);
    context->PSGetSamplers(0, 5, oldSamplers);
    context->OMGetBlendState(&oldBlend, oldBlendFactor, &oldSampleMask);
    context->OMGetDepthStencilState(&oldDepth, &oldStencilReference);
    context->RSGetState(&oldRasterizer);
    context->RSGetViewports(&oldViewportCount, oldViewports);
    context->RSGetScissorRects(&oldScissorCount, oldScissors);

    ID3D11Buffer* vertexBuffers[2] = {
        g_m18PeakVertexBuffer, g_m18PeakSecondaryBuffer,
    };
    const UINT strides[2] = {g_EndfieldM18PeakVertexStride, 0u};
    const UINT offsets[2] = {};
    const FLOAT blendFactor[4] = {1.0f, 1.0f, 1.0f, 1.0f};
    context->IASetInputLayout(g_m18PeakInputLayout);
    context->IASetVertexBuffers(0, 2, vertexBuffers, strides, offsets);
    context->IASetIndexBuffer(g_m18PeakIndexBuffer, DXGI_FORMAT_R16_UINT, 0);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_m18PeakVertexShader, nullptr, 0);
    context->PSSetShader(g_m18PeakPixelShader, nullptr, 0);
    context->VSSetConstantBuffers(0, 5, g_m18PeakVertexConstantBuffers);
    context->PSSetConstantBuffers(0, 4, g_m18PeakPixelConstantBuffers);
    context->VSSetShaderResources(0, 1, &g_m14SkinView);
    context->PSSetShaderResources(0, 5, textureViews);
    context->PSSetSamplers(0, 5, g_m18PeakSamplers);
    context->OMSetBlendState(g_m18PeakBlendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(g_m18PeakDepthState, 0);
    context->RSSetState(g_m18PeakRasterizerState);
    const D3D11_VIEWPORT viewport = {
        0.0f, 0.0f, static_cast<float>(g_m18PeakResourceWidth),
        static_cast<float>(g_m18PeakResourceHeight), 0.0f, 1.0f};
    const D3D11_RECT scissor = {
        0, 0, static_cast<LONG>(g_m18PeakResourceWidth),
        static_cast<LONG>(g_m18PeakResourceHeight)};
    context->RSSetViewports(1, &viewport);
    context->RSSetScissorRects(1, &scissor);
    context->DrawIndexed(g_EndfieldM18PeakIndexCount, 0, 0);

    ID3D11ShaderResourceView* nullVSView = nullptr;
    ID3D11ShaderResourceView* nullPSViews[5] = {};
    context->VSSetShaderResources(0, 1, &nullVSView);
    context->PSSetShaderResources(0, 5, nullPSViews);
    context->IASetInputLayout(oldLayout);
    context->IASetVertexBuffers(0, 2, oldVBs, oldStrides, oldOffsets);
    context->IASetIndexBuffer(oldIB, oldIndexFormat, oldIndexOffset);
    context->IASetPrimitiveTopology(oldTopology);
    context->VSSetShader(oldVS, nullptr, 0);
    context->PSSetShader(oldPS, nullptr, 0);
    context->VSSetConstantBuffers(0, 5, oldVSCBs);
    context->PSSetConstantBuffers(0, 4, oldPSCBs);
    context->VSSetShaderResources(0, 1, &oldVSView);
    context->PSSetShaderResources(0, 5, oldPSViews);
    context->PSSetSamplers(0, 5, oldSamplers);
    context->OMSetBlendState(oldBlend, oldBlendFactor, oldSampleMask);
    context->OMSetDepthStencilState(oldDepth, oldStencilReference);
    context->RSSetState(oldRasterizer);
    context->RSSetViewports(oldViewportCount, oldViewports);
    context->RSSetScissorRects(oldScissorCount, oldScissors);

    for (ID3D11SamplerState*& value : oldSamplers) ReleaseM14Object(value);
    for (ID3D11ShaderResourceView*& value : oldPSViews) ReleaseM14Object(value);
    ReleaseM14Object(oldVSView);
    for (ID3D11Buffer*& value : oldPSCBs) ReleaseM14Object(value);
    for (ID3D11Buffer*& value : oldVSCBs) ReleaseM14Object(value);
    ReleaseM14Object(oldRasterizer);
    ReleaseM14Object(oldDepth);
    ReleaseM14Object(oldBlend);
    ReleaseM14Object(oldIB);
    for (ID3D11Buffer*& value : oldVBs) ReleaseM14Object(value);
    ReleaseM14Object(oldLayout);
    ReleaseM14Object(oldPS);
    ReleaseM14Object(oldVS);
    ReleaseM14Object(renderDepth);
    ReleaseM14Object(renderTarget);
    context->Release();
    for (ID3D11ShaderResourceView*& view : textureViews)
        ReleaseM14Object(view);
    g_m18PeakDrawCount.fetch_add(1, std::memory_order_relaxed);
    g_m18PeakLastResult.store(S_OK, std::memory_order_relaxed);
}

void UNITY_INTERFACE_API DrawM28PeakExactRuntime(int eventId)
{
    if (eventId != 0)
        return;
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_m28PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m28PeakLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    HRESULT result = CreateM14RuntimeResources(device);
    if (FAILED(result))
    {
        ReleaseM14RuntimeResources();
        g_m28PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m28PeakLastResult.store(result, std::memory_order_relaxed);
        return;
    }
    result = EnsureM28ScreenConstantBuffers(device);
    if (FAILED(result))
    {
        g_m28PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m28PeakLastResult.store(result, std::memory_order_relaxed);
        return;
    }
    ID3D11Resource* textureResources[3] = {};
    for (std::size_t slot = 0; slot < 3; ++slot)
    {
        textureResources[slot] = reinterpret_cast<ID3D11Resource*>(
            g_m28PeakTextures[slot].load(std::memory_order_acquire));
        if (textureResources[slot] == nullptr)
        {
            g_m28PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
            g_m28PeakLastResult.store(E_POINTER, std::memory_order_relaxed);
            return;
        }
    }
    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        g_m28PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m28PeakLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    ID3D11RenderTargetView* renderTargets[2] = {};
    ID3D11DepthStencilView* renderDepth = nullptr;
    context->OMGetRenderTargets(2, renderTargets, &renderDepth);
    ID3D11Resource* outputResources[2] = {};
    for (std::size_t target = 0; target < 2; ++target)
    {
        if (renderTargets[target] != nullptr)
            renderTargets[target]->GetResource(&outputResources[target]);
    }
    const bool invalidOutputs = renderTargets[0] == nullptr ||
        renderTargets[1] == nullptr || renderDepth == nullptr ||
        g_m14SkinView == nullptr;
    const bool sceneColorAliasesOutput = textureResources[2] == outputResources[0] ||
        textureResources[2] == outputResources[1];
    if (invalidOutputs || sceneColorAliasesOutput)
    {
        for (ID3D11Resource*& resource : outputResources)
            ReleaseM14Object(resource);
        ReleaseM14Object(renderDepth);
        for (ID3D11RenderTargetView*& target : renderTargets)
            ReleaseM14Object(target);
        context->Release();
        g_m28PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m28PeakLastResult.store(
            sceneColorAliasesOutput ? DXGI_ERROR_INVALID_CALL : E_INVALIDARG,
            std::memory_order_relaxed);
        return;
    }
    ID3D11ShaderResourceView* textureViews[3] = {};
    for (std::size_t slot = 0; slot < 3; ++slot)
    {
        result = CreateDiagnosticShaderResourceView(
            device, textureResources[slot], &textureViews[slot]);
        if (FAILED(result) || textureViews[slot] == nullptr)
        {
            for (ID3D11ShaderResourceView*& view : textureViews)
                ReleaseM14Object(view);
            for (ID3D11Resource*& resource : outputResources)
                ReleaseM14Object(resource);
            ReleaseM14Object(renderDepth);
            for (ID3D11RenderTargetView*& target : renderTargets)
                ReleaseM14Object(target);
            context->Release();
            g_m28PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
            g_m28PeakLastResult.store(
                FAILED(result) ? result : E_POINTER, std::memory_order_relaxed);
            return;
        }
    }

    ID3D11VertexShader* oldVS = nullptr;
    ID3D11PixelShader* oldPS = nullptr;
    ID3D11InputLayout* oldLayout = nullptr;
    ID3D11Buffer* oldVBs[2] = {};
    ID3D11Buffer* oldIB = nullptr;
    ID3D11Buffer* oldVSCBs[5] = {};
    ID3D11Buffer* oldPSCBs[4] = {};
    ID3D11ShaderResourceView* oldVSView = nullptr;
    ID3D11ShaderResourceView* oldPSViews[3] = {};
    ID3D11SamplerState* oldSamplers[3] = {};
    ID3D11BlendState* oldBlend = nullptr;
    ID3D11DepthStencilState* oldDepth = nullptr;
    ID3D11RasterizerState* oldRasterizer = nullptr;
    D3D11_PRIMITIVE_TOPOLOGY oldTopology = D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    DXGI_FORMAT oldIndexFormat = DXGI_FORMAT_UNKNOWN;
    UINT oldStrides[2] = {};
    UINT oldOffsets[2] = {};
    UINT oldIndexOffset = 0;
    FLOAT oldBlendFactor[4] = {};
    UINT oldSampleMask = 0;
    UINT oldStencilReference = 0;
    UINT oldViewportCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_VIEWPORT oldViewports[
        D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    UINT oldScissorCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_RECT oldScissors[
        D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    context->VSGetShader(&oldVS, nullptr, nullptr);
    context->PSGetShader(&oldPS, nullptr, nullptr);
    context->IAGetInputLayout(&oldLayout);
    context->IAGetVertexBuffers(0, 2, oldVBs, oldStrides, oldOffsets);
    context->IAGetIndexBuffer(&oldIB, &oldIndexFormat, &oldIndexOffset);
    context->IAGetPrimitiveTopology(&oldTopology);
    context->VSGetConstantBuffers(0, 5, oldVSCBs);
    context->PSGetConstantBuffers(0, 4, oldPSCBs);
    context->VSGetShaderResources(0, 1, &oldVSView);
    context->PSGetShaderResources(0, 3, oldPSViews);
    context->PSGetSamplers(0, 3, oldSamplers);
    context->OMGetBlendState(&oldBlend, oldBlendFactor, &oldSampleMask);
    context->OMGetDepthStencilState(&oldDepth, &oldStencilReference);
    context->RSGetState(&oldRasterizer);
    context->RSGetViewports(&oldViewportCount, oldViewports);
    context->RSGetScissorRects(&oldScissorCount, oldScissors);

    ID3D11Buffer* vertexBuffers[2] = {
        g_m28PeakVertexBuffer, g_m28PeakSecondaryBuffer,
    };
    const UINT strides[2] = {g_EndfieldM28PeakVertexStride, 0u};
    const UINT offsets[2] = {};
    const FLOAT blendFactor[4] = {1.0f, 1.0f, 1.0f, 1.0f};
    context->IASetInputLayout(g_m28PeakInputLayout);
    context->IASetVertexBuffers(0, 2, vertexBuffers, strides, offsets);
    context->IASetIndexBuffer(g_m28PeakIndexBuffer, DXGI_FORMAT_R16_UINT, 0);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_m28PeakVertexShader, nullptr, 0);
    context->PSSetShader(g_m28PeakPixelShader, nullptr, 0);
    context->VSSetConstantBuffers(0, 5, g_m28PeakVertexConstantBuffers);
    context->PSSetConstantBuffers(0, 4, g_m28PeakPixelConstantBuffers);
    context->VSSetShaderResources(0, 1, &g_m14SkinView);
    context->PSSetShaderResources(0, 3, textureViews);
    context->PSSetSamplers(0, 3, g_m28PeakSamplers);
    context->OMSetBlendState(g_m28PeakBlendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(g_m28PeakDepthState, 0);
    context->RSSetState(g_m28PeakRasterizerState);
    const D3D11_VIEWPORT viewport = {
        0.0f, 0.0f, static_cast<float>(g_m28PeakResourceWidth),
        static_cast<float>(g_m28PeakResourceHeight), 0.0f, 1.0f};
    const D3D11_RECT scissor = {
        0, 0, static_cast<LONG>(g_m28PeakResourceWidth),
        static_cast<LONG>(g_m28PeakResourceHeight)};
    context->RSSetViewports(1, &viewport);
    context->RSSetScissorRects(1, &scissor);
    context->DrawIndexedInstanced(
        g_EndfieldM28PeakIndexCount, 1u, 0u, 0, 0u);

    ID3D11ShaderResourceView* nullVSView = nullptr;
    ID3D11ShaderResourceView* nullPSViews[3] = {};
    context->VSSetShaderResources(0, 1, &nullVSView);
    context->PSSetShaderResources(0, 3, nullPSViews);
    context->IASetInputLayout(oldLayout);
    context->IASetVertexBuffers(0, 2, oldVBs, oldStrides, oldOffsets);
    context->IASetIndexBuffer(oldIB, oldIndexFormat, oldIndexOffset);
    context->IASetPrimitiveTopology(oldTopology);
    context->VSSetShader(oldVS, nullptr, 0);
    context->PSSetShader(oldPS, nullptr, 0);
    context->VSSetConstantBuffers(0, 5, oldVSCBs);
    context->PSSetConstantBuffers(0, 4, oldPSCBs);
    context->VSSetShaderResources(0, 1, &oldVSView);
    context->PSSetShaderResources(0, 3, oldPSViews);
    context->PSSetSamplers(0, 3, oldSamplers);
    context->OMSetBlendState(oldBlend, oldBlendFactor, oldSampleMask);
    context->OMSetDepthStencilState(oldDepth, oldStencilReference);
    context->RSSetState(oldRasterizer);
    context->RSSetViewports(oldViewportCount, oldViewports);
    context->RSSetScissorRects(oldScissorCount, oldScissors);

    for (ID3D11SamplerState*& value : oldSamplers) ReleaseM14Object(value);
    for (ID3D11ShaderResourceView*& value : oldPSViews) ReleaseM14Object(value);
    ReleaseM14Object(oldVSView);
    for (ID3D11Buffer*& value : oldPSCBs) ReleaseM14Object(value);
    for (ID3D11Buffer*& value : oldVSCBs) ReleaseM14Object(value);
    ReleaseM14Object(oldRasterizer);
    ReleaseM14Object(oldDepth);
    ReleaseM14Object(oldBlend);
    ReleaseM14Object(oldIB);
    for (ID3D11Buffer*& value : oldVBs) ReleaseM14Object(value);
    ReleaseM14Object(oldLayout);
    ReleaseM14Object(oldPS);
    ReleaseM14Object(oldVS);
    for (ID3D11ShaderResourceView*& view : textureViews)
        ReleaseM14Object(view);
    for (ID3D11Resource*& resource : outputResources)
        ReleaseM14Object(resource);
    ReleaseM14Object(renderDepth);
    for (ID3D11RenderTargetView*& target : renderTargets)
        ReleaseM14Object(target);
    context->Release();
    g_m28PeakDrawCount.fetch_add(1, std::memory_order_relaxed);
    g_m28PeakLastResult.store(S_OK, std::memory_order_relaxed);
}

void UNITY_INTERFACE_API DrawM21PeakExactRuntime(int eventId)
{
    if (eventId != 0)
        return;
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_m21PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m21PeakLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    HRESULT result = CreateM14RuntimeResources(device);
    if (SUCCEEDED(result))
        result = EnsureM21PeakScreenConstantBuffers(device);
    if (FAILED(result))
    {
        ReleaseM14RuntimeResources();
        g_m21PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m21PeakLastResult.store(result, std::memory_order_relaxed);
        return;
    }
    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        g_m21PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m21PeakLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    ID3D11RenderTargetView* renderTarget = nullptr;
    ID3D11DepthStencilView* renderDepth = nullptr;
    context->OMGetRenderTargets(1, &renderTarget, &renderDepth);
    if (renderTarget == nullptr || renderDepth == nullptr ||
        g_m14SkinView == nullptr || g_m21PeakWhiteView == nullptr)
    {
        ReleaseM14Object(renderDepth);
        ReleaseM14Object(renderTarget);
        context->Release();
        g_m21PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m21PeakLastResult.store(E_INVALIDARG, std::memory_order_relaxed);
        return;
    }

    ID3D11VertexShader* oldVS = nullptr;
    ID3D11PixelShader* oldPS = nullptr;
    ID3D11InputLayout* oldLayout = nullptr;
    ID3D11Buffer* oldVBs[2] = {};
    ID3D11Buffer* oldIB = nullptr;
    ID3D11Buffer* oldVSCBs[5] = {};
    ID3D11Buffer* oldPSCBs[5] = {};
    ID3D11ShaderResourceView* oldVSView = nullptr;
    ID3D11ShaderResourceView* oldPSView = nullptr;
    ID3D11SamplerState* oldSampler = nullptr;
    ID3D11BlendState* oldBlend = nullptr;
    ID3D11DepthStencilState* oldDepth = nullptr;
    ID3D11RasterizerState* oldRasterizer = nullptr;
    D3D11_PRIMITIVE_TOPOLOGY oldTopology = D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    DXGI_FORMAT oldIndexFormat = DXGI_FORMAT_UNKNOWN;
    UINT oldStrides[2] = {};
    UINT oldOffsets[2] = {};
    UINT oldIndexOffset = 0;
    FLOAT oldBlendFactor[4] = {};
    UINT oldSampleMask = 0;
    UINT oldStencilReference = 0;
    UINT oldViewportCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_VIEWPORT oldViewports[
        D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    UINT oldScissorCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_RECT oldScissors[
        D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    context->VSGetShader(&oldVS, nullptr, nullptr);
    context->PSGetShader(&oldPS, nullptr, nullptr);
    context->IAGetInputLayout(&oldLayout);
    context->IAGetVertexBuffers(0, 2, oldVBs, oldStrides, oldOffsets);
    context->IAGetIndexBuffer(&oldIB, &oldIndexFormat, &oldIndexOffset);
    context->IAGetPrimitiveTopology(&oldTopology);
    context->VSGetConstantBuffers(0, 5, oldVSCBs);
    context->PSGetConstantBuffers(0, 5, oldPSCBs);
    context->VSGetShaderResources(0, 1, &oldVSView);
    context->PSGetShaderResources(0, 1, &oldPSView);
    context->PSGetSamplers(0, 1, &oldSampler);
    context->OMGetBlendState(&oldBlend, oldBlendFactor, &oldSampleMask);
    context->OMGetDepthStencilState(&oldDepth, &oldStencilReference);
    context->RSGetState(&oldRasterizer);
    context->RSGetViewports(&oldViewportCount, oldViewports);
    context->RSGetScissorRects(&oldScissorCount, oldScissors);

    ID3D11Buffer* vertexBuffers[2] = {
        g_m21PeakVertexBuffer, g_m21PeakSecondaryBuffer,
    };
    const UINT strides[2] = {g_EndfieldM21PeakVertexStride, 0u};
    const UINT offsets[2] = {};
    const FLOAT blendFactor[4] = {1.0f, 1.0f, 1.0f, 1.0f};
    context->IASetInputLayout(g_m21PeakInputLayout);
    context->IASetVertexBuffers(0, 2, vertexBuffers, strides, offsets);
    context->IASetIndexBuffer(g_m21PeakIndexBuffer, DXGI_FORMAT_R16_UINT, 0);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_m21PeakVertexShader, nullptr, 0);
    context->PSSetShader(g_m21PeakPixelShader, nullptr, 0);
    context->VSSetConstantBuffers(0, 5, g_m21PeakVertexConstantBuffers);
    context->PSSetConstantBuffers(0, 5, g_m21PeakPixelConstantBuffers);
    context->VSSetShaderResources(0, 1, &g_m14SkinView);
    context->PSSetShaderResources(0, 1, &g_m21PeakWhiteView);
    context->PSSetSamplers(0, 1, &g_m21PeakSampler);
    context->OMSetBlendState(g_m21PeakBlendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(g_m21PeakDepthState, 0);
    context->RSSetState(g_m21PeakRasterizerState);
    const D3D11_VIEWPORT viewport = {
        0.0f, 0.0f, static_cast<float>(g_m21PeakResourceWidth),
        static_cast<float>(g_m21PeakResourceHeight), 0.0f, 1.0f};
    const D3D11_RECT scissor = {
        0, 0, static_cast<LONG>(g_m21PeakResourceWidth),
        static_cast<LONG>(g_m21PeakResourceHeight)};
    context->RSSetViewports(1, &viewport);
    context->RSSetScissorRects(1, &scissor);
    context->DrawIndexed(g_EndfieldM21PeakIndexCount, 0, 0);

    ID3D11ShaderResourceView* nullView = nullptr;
    context->VSSetShaderResources(0, 1, &nullView);
    context->PSSetShaderResources(0, 1, &nullView);
    context->IASetInputLayout(oldLayout);
    context->IASetVertexBuffers(0, 2, oldVBs, oldStrides, oldOffsets);
    context->IASetIndexBuffer(oldIB, oldIndexFormat, oldIndexOffset);
    context->IASetPrimitiveTopology(oldTopology);
    context->VSSetShader(oldVS, nullptr, 0);
    context->PSSetShader(oldPS, nullptr, 0);
    context->VSSetConstantBuffers(0, 5, oldVSCBs);
    context->PSSetConstantBuffers(0, 5, oldPSCBs);
    context->VSSetShaderResources(0, 1, &oldVSView);
    context->PSSetShaderResources(0, 1, &oldPSView);
    context->PSSetSamplers(0, 1, &oldSampler);
    context->OMSetBlendState(oldBlend, oldBlendFactor, oldSampleMask);
    context->OMSetDepthStencilState(oldDepth, oldStencilReference);
    context->RSSetState(oldRasterizer);
    context->RSSetViewports(oldViewportCount, oldViewports);
    context->RSSetScissorRects(oldScissorCount, oldScissors);

    ReleaseM14Object(oldSampler);
    ReleaseM14Object(oldPSView);
    ReleaseM14Object(oldVSView);
    for (ID3D11Buffer*& value : oldPSCBs) ReleaseM14Object(value);
    for (ID3D11Buffer*& value : oldVSCBs) ReleaseM14Object(value);
    ReleaseM14Object(oldRasterizer);
    ReleaseM14Object(oldDepth);
    ReleaseM14Object(oldBlend);
    ReleaseM14Object(oldIB);
    for (ID3D11Buffer*& value : oldVBs) ReleaseM14Object(value);
    ReleaseM14Object(oldLayout);
    ReleaseM14Object(oldPS);
    ReleaseM14Object(oldVS);
    ReleaseM14Object(renderDepth);
    ReleaseM14Object(renderTarget);
    context->Release();
    g_m21PeakDrawCount.fetch_add(1, std::memory_order_relaxed);
    g_m21PeakLastResult.store(S_OK, std::memory_order_relaxed);
}

void UNITY_INTERFACE_API DrawM20PeakExactRuntime(int eventId)
{
    if (eventId != 0) return;
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_m20PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m20PeakLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    HRESULT result = CreateM14RuntimeResources(device);
    if (SUCCEEDED(result))
        result = EnsureM20ScreenConstantBuffers(device);
    if (FAILED(result))
    {
        ReleaseM14RuntimeResources();
        g_m20PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m20PeakLastResult.store(result, std::memory_order_relaxed);
        return;
    }
    ID3D11Resource* depthResource = reinterpret_cast<ID3D11Resource*>(
        g_m20PeakDepthTexture.load(std::memory_order_acquire));
    ID3D11ShaderResourceView* depthView = nullptr;
    result = CreateDiagnosticShaderResourceView(device, depthResource, &depthView);
    if (FAILED(result) || depthView == nullptr || g_m20PeakAtlasView == nullptr ||
        g_m20PeakVertexView == nullptr)
    {
        ReleaseM14Object(depthView);
        g_m20PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m20PeakLastResult.store(FAILED(result) ? result : E_POINTER,
                                  std::memory_order_relaxed);
        return;
    }
    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        ReleaseM14Object(depthView);
        g_m20PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m20PeakLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    ID3D11RenderTargetView* renderTargets[2] = {};
    ID3D11DepthStencilView* renderDepth = nullptr;
    context->OMGetRenderTargets(2, renderTargets, &renderDepth);
    if (renderTargets[0] == nullptr || renderTargets[1] == nullptr ||
        renderDepth == nullptr)
    {
        ReleaseM14Object(renderDepth);
        ReleaseM14Object(renderTargets[1]);
        ReleaseM14Object(renderTargets[0]);
        ReleaseM14Object(depthView);
        context->Release();
        g_m20PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m20PeakLastResult.store(E_INVALIDARG, std::memory_order_relaxed);
        return;
    }

    ID3D11VertexShader* oldVS = nullptr;
    ID3D11PixelShader* oldPS = nullptr;
    ID3D11InputLayout* oldLayout = nullptr;
    ID3D11Buffer* oldVBs[2] = {};
    ID3D11Buffer* oldIB = nullptr;
    ID3D11Buffer* oldVSCBs[5] = {};
    ID3D11Buffer* oldPSCBs[4] = {};
    ID3D11ShaderResourceView* oldVSView = nullptr;
    ID3D11ShaderResourceView* oldPSViews[2] = {};
    ID3D11SamplerState* oldSamplers[2] = {};
    ID3D11BlendState* oldBlend = nullptr;
    ID3D11DepthStencilState* oldDepth = nullptr;
    ID3D11RasterizerState* oldRasterizer = nullptr;
    D3D11_PRIMITIVE_TOPOLOGY oldTopology = D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    DXGI_FORMAT oldIndexFormat = DXGI_FORMAT_UNKNOWN;
    UINT oldStrides[2] = {};
    UINT oldOffsets[2] = {};
    UINT oldIndexOffset = 0;
    FLOAT oldBlendFactor[4] = {};
    UINT oldSampleMask = 0;
    UINT oldStencilReference = 0;
    context->VSGetShader(&oldVS, nullptr, nullptr);
    context->PSGetShader(&oldPS, nullptr, nullptr);
    context->IAGetInputLayout(&oldLayout);
    context->IAGetVertexBuffers(0, 2, oldVBs, oldStrides, oldOffsets);
    context->IAGetIndexBuffer(&oldIB, &oldIndexFormat, &oldIndexOffset);
    context->IAGetPrimitiveTopology(&oldTopology);
    context->VSGetConstantBuffers(0, 5, oldVSCBs);
    context->PSGetConstantBuffers(0, 4, oldPSCBs);
    context->VSGetShaderResources(0, 1, &oldVSView);
    context->PSGetShaderResources(0, 2, oldPSViews);
    context->PSGetSamplers(0, 2, oldSamplers);
    context->OMGetBlendState(&oldBlend, oldBlendFactor, &oldSampleMask);
    context->OMGetDepthStencilState(&oldDepth, &oldStencilReference);
    context->RSGetState(&oldRasterizer);
    UINT oldViewportCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_VIEWPORT oldViewports[D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    context->RSGetViewports(&oldViewportCount, oldViewports);
    UINT oldScissorCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_RECT oldScissors[D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    context->RSGetScissorRects(&oldScissorCount, oldScissors);

    ID3D11Buffer* vertexBuffers[2] = {
        g_m20PeakVertexBuffer, g_m20PeakSecondaryBuffer,
    };
    const UINT strides[2] = {g_EndfieldM20PeakVertexStride, 0u};
    const UINT offsets[2] = {};
    ID3D11ShaderResourceView* pixelViews[2] = {depthView, g_m20PeakAtlasView};
    const FLOAT blendFactor[4] = {1.0f, 1.0f, 1.0f, 1.0f};
    context->IASetInputLayout(g_m20PeakInputLayout);
    context->IASetVertexBuffers(0, 2, vertexBuffers, strides, offsets);
    context->IASetIndexBuffer(g_m20PeakIndexBuffer, DXGI_FORMAT_R16_UINT, 0);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_m20PeakVertexShader, nullptr, 0);
    context->PSSetShader(g_m20PeakPixelShader, nullptr, 0);
    context->VSSetConstantBuffers(0, 5, g_m20PeakVertexConstantBuffers);
    context->PSSetConstantBuffers(0, 4, g_m20PeakPixelConstantBuffers);
    context->VSSetShaderResources(0, 1, &g_m20PeakVertexView);
    context->PSSetShaderResources(0, 2, pixelViews);
    context->PSSetSamplers(0, 2, g_m20PeakSamplers);
    context->OMSetBlendState(g_m20PeakBlendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(g_m20PeakDepthState, 0);
    context->RSSetState(g_m20PeakRasterizerState);
    const D3D11_VIEWPORT viewport = {
        0.0f, 0.0f, static_cast<float>(g_m20PeakResourceWidth),
        static_cast<float>(g_m20PeakResourceHeight), 0.0f, 1.0f};
    const D3D11_RECT scissor = {
        0, 0, static_cast<LONG>(g_m20PeakResourceWidth),
        static_cast<LONG>(g_m20PeakResourceHeight)};
    context->RSSetViewports(1, &viewport);
    context->RSSetScissorRects(1, &scissor);
    context->DrawIndexedInstanced(g_EndfieldM20PeakIndexCount, 1u, 0u, 0, 0u);

    ID3D11ShaderResourceView* nullVSView = nullptr;
    ID3D11ShaderResourceView* nullPSViews[2] = {};
    context->VSSetShaderResources(0, 1, &nullVSView);
    context->PSSetShaderResources(0, 2, nullPSViews);
    context->IASetInputLayout(oldLayout);
    context->IASetVertexBuffers(0, 2, oldVBs, oldStrides, oldOffsets);
    context->IASetIndexBuffer(oldIB, oldIndexFormat, oldIndexOffset);
    context->IASetPrimitiveTopology(oldTopology);
    context->VSSetShader(oldVS, nullptr, 0);
    context->PSSetShader(oldPS, nullptr, 0);
    context->VSSetConstantBuffers(0, 5, oldVSCBs);
    context->PSSetConstantBuffers(0, 4, oldPSCBs);
    context->VSSetShaderResources(0, 1, &oldVSView);
    context->PSSetShaderResources(0, 2, oldPSViews);
    context->PSSetSamplers(0, 2, oldSamplers);
    context->OMSetBlendState(oldBlend, oldBlendFactor, oldSampleMask);
    context->OMSetDepthStencilState(oldDepth, oldStencilReference);
    context->RSSetState(oldRasterizer);
    context->RSSetViewports(oldViewportCount, oldViewports);
    context->RSSetScissorRects(oldScissorCount, oldScissors);

    for (ID3D11SamplerState*& value : oldSamplers) ReleaseM14Object(value);
    for (ID3D11ShaderResourceView*& value : oldPSViews) ReleaseM14Object(value);
    ReleaseM14Object(oldVSView);
    for (ID3D11Buffer*& value : oldPSCBs) ReleaseM14Object(value);
    for (ID3D11Buffer*& value : oldVSCBs) ReleaseM14Object(value);
    ReleaseM14Object(oldRasterizer);
    ReleaseM14Object(oldDepth);
    ReleaseM14Object(oldBlend);
    ReleaseM14Object(oldIB);
    for (ID3D11Buffer*& value : oldVBs) ReleaseM14Object(value);
    ReleaseM14Object(oldLayout);
    ReleaseM14Object(oldPS);
    ReleaseM14Object(oldVS);
    ReleaseM14Object(renderDepth);
    ReleaseM14Object(renderTargets[1]);
    ReleaseM14Object(renderTargets[0]);
    ReleaseM14Object(depthView);
    context->Release();
    g_m20PeakDrawCount.fetch_add(1, std::memory_order_relaxed);
    g_m20PeakLastResult.store(S_OK, std::memory_order_relaxed);
}

void UNITY_INTERFACE_API DrawM31PeakExactRuntime(int eventId)
{
    if (eventId < 0 ||
        static_cast<std::uint32_t>(eventId) >=
            g_EndfieldM31PeakMaxEventCount)
        return;
    const std::uint32_t temporalPacketIndex =
        g_m31PeakTemporalPacketIndex.load(std::memory_order_acquire);
    if (temporalPacketIndex >= g_EndfieldM31PeakTemporalPacketCount)
    {
        g_m31PeakFailureCount.fetch_add(1u, std::memory_order_relaxed);
        g_m31PeakLastResult.store(E_INVALIDARG, std::memory_order_relaxed);
        return;
    }
    const EndfieldM31PeakTemporalPacket& temporalPacket =
        g_EndfieldM31PeakTemporalPackets[temporalPacketIndex];
    const bool supportedSchedule =
        (temporalPacket.scheduleProfile ==
                g_EndfieldM31PeakScheduleQueue3000Interval2 &&
            temporalPacket.drawCount == 2u) ||
        (temporalPacket.scheduleProfile ==
                g_EndfieldM31PeakScheduleQueue3000ThenPostM18_3 &&
            temporalPacket.drawCount == 3u);
    if (!temporalPacket.chronologyValidated || !supportedSchedule ||
        static_cast<std::uint32_t>(eventId) >= temporalPacket.drawCount ||
        temporalPacket.firstDrawPayload + temporalPacket.drawCount >
            g_EndfieldM31PeakDrawPayloadCount)
    {
        g_m31PeakFailureCount.fetch_add(1u, std::memory_order_relaxed);
        g_m31PeakLastResult.store(E_INVALIDARG, std::memory_order_relaxed);
        return;
    }
    const std::uint32_t drawPayloadIndex =
        temporalPacket.firstDrawPayload + static_cast<std::uint32_t>(eventId);
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_m31PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m31PeakLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    HRESULT result = CreateM14RuntimeResources(device);
    if (FAILED(result))
    {
        ReleaseM14RuntimeResources();
        g_m31PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m31PeakLastResult.store(result, std::memory_order_relaxed);
        return;
    }

    ID3D11Resource* depthResource = reinterpret_cast<ID3D11Resource*>(
        g_m31PeakDepthTexture.load(std::memory_order_acquire));
    ID3D11ShaderResourceView* depthView = nullptr;
    ID3D11DepthStencilView* m31DepthView = nullptr;
    result = CreateDiagnosticShaderResourceView(
        device, depthResource, &depthView);
    if (SUCCEEDED(result))
        result = CreateM31ReadOnlyDepthStencilView(
            device, depthResource, &m31DepthView);
    if (FAILED(result) || depthView == nullptr || m31DepthView == nullptr ||
        g_m31PeakMainView == nullptr || g_m31PeakSamplers[0] == nullptr ||
        g_m31PeakSamplers[1] == nullptr || g_m31PeakBlendState == nullptr ||
        g_m31PeakDepthState == nullptr || g_m31PeakRasterizerState == nullptr)
    {
        ReleaseM14Object(m31DepthView);
        ReleaseM14Object(depthView);
        g_m31PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m31PeakLastResult.store(
            FAILED(result) ? result : E_POINTER, std::memory_order_relaxed);
        return;
    }

    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        ReleaseM14Object(m31DepthView);
        ReleaseM14Object(depthView);
        g_m31PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m31PeakLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }

    ID3D11RenderTargetView* renderTargets[2] = {};
    ID3D11DepthStencilView* renderDepth = nullptr;
    context->OMGetRenderTargets(2, renderTargets, &renderDepth);
    if (renderTargets[0] == nullptr || renderTargets[1] == nullptr ||
        !ValidateM31OutputCompatibility(renderTargets, depthResource))
    {
        ReleaseM14Object(renderDepth);
        ReleaseM14Object(renderTargets[1]);
        ReleaseM14Object(renderTargets[0]);
        ReleaseM14Object(m31DepthView);
        ReleaseM14Object(depthView);
        context->Release();
        g_m31PeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m31PeakLastResult.store(E_INVALIDARG, std::memory_order_relaxed);
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

    const FLOAT blendFactor[4] = {1.0f, 1.0f, 1.0f, 1.0f};
    const EndfieldM31PeakPacketPayload& packet =
        g_EndfieldM31PeakDrawPayloads[drawPayloadIndex];
    ID3D11Buffer* vertexBuffers[2] = {
        g_m31PeakVertexBuffers[drawPayloadIndex],
        g_m31PeakSecondaryBuffers[drawPayloadIndex],
    };
    const UINT strides[2] = {g_EndfieldM31PeakVertexStride, 0u};
    const UINT offsets[2] = {};
    ID3D11ShaderResourceView* pixelViews[2] = {
        depthView, g_m31PeakMainView,
    };
    context->IASetInputLayout(g_m14InputLayout);
    context->IASetVertexBuffers(0, 2, vertexBuffers, strides, offsets);
    context->IASetIndexBuffer(
        g_m31PeakIndexBuffers[drawPayloadIndex], DXGI_FORMAT_R16_UINT, 0);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_m14RuntimeVertexShader, nullptr, 0);
    context->PSSetShader(g_m14RuntimePixelShader, nullptr, 0);
    context->VSSetConstantBuffers(
        0, 5, g_m31PeakVertexConstantBuffers[drawPayloadIndex]);
    context->PSSetConstantBuffers(
        0, 4, g_m31PeakPixelConstantBuffers[drawPayloadIndex]);
    context->OMSetRenderTargets(2, renderTargets, m31DepthView);
    context->VSSetShaderResources(0, 1, &g_m14SkinView);
    context->PSSetShaderResources(0, 2, pixelViews);
    context->PSSetSamplers(0, 2, g_m31PeakSamplers);
    context->OMSetBlendState(g_m31PeakBlendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(g_m31PeakDepthState, 0);
    context->RSSetState(g_m31PeakRasterizerState);
    const bool boundStateValid = ValidateM31BoundState(
        context, renderTargets, m31DepthView, pixelViews);
    if (boundStateValid)
        context->DrawIndexed(packet.indexCount, 0, 0);

    ID3D11ShaderResourceView* nullVertexView = nullptr;
    ID3D11ShaderResourceView* nullPixelViews[2] = {};
    context->VSSetShaderResources(0, 1, &nullVertexView);
    context->PSSetShaderResources(0, 2, nullPixelViews);
    context->OMSetRenderTargets(2, renderTargets, renderDepth);
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
    ReleaseM14Object(m31DepthView);
    ReleaseM14Object(depthView);
    context->Release();

    if (boundStateValid)
    {
        g_m31PeakDrawCount.fetch_add(1u, std::memory_order_relaxed);
        g_m31PeakLastResult.store(S_OK, std::memory_order_relaxed);
    }
    else
    {
        g_m31PeakFailureCount.fetch_add(1u, std::memory_order_relaxed);
        g_m31PeakLastResult.store(E_FAIL, std::memory_order_relaxed);
    }
}

void UNITY_INTERFACE_API DrawVFXBaseV2PeakCohortRuntime(int eventId)
{
    if (eventId != 0 && eventId != 1)
        return;
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_vfxPeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_vfxPeakLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    HRESULT result = CreateM14RuntimeResources(device);
    if (FAILED(result))
    {
        ReleaseM14RuntimeResources();
        g_vfxPeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_vfxPeakLastResult.store(result, std::memory_order_relaxed);
        return;
    }
    ID3D11Resource* depthResource = reinterpret_cast<ID3D11Resource*>(
        g_vfxPeakDepthTexture.load(std::memory_order_acquire));
    ID3D11ShaderResourceView* depthView = nullptr;
    result = CreateDiagnosticShaderResourceView(device, depthResource, &depthView);
    if (FAILED(result) || depthView == nullptr)
    {
        ReleaseM14Object(depthView);
        g_vfxPeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_vfxPeakLastResult.store(
            FAILED(result) ? result : E_POINTER, std::memory_order_relaxed);
        return;
    }
    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        ReleaseM14Object(depthView);
        g_vfxPeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_vfxPeakLastResult.store(E_POINTER, std::memory_order_relaxed);
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
        ReleaseM14Object(depthView);
        context->Release();
        g_vfxPeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_vfxPeakLastResult.store(E_INVALIDARG, std::memory_order_relaxed);
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

    const std::uint32_t firstDraw = eventId == 0 ? 0u : 1u;
    const std::uint32_t endDraw = eventId == 0 ? 1u : g_EndfieldVFXPeakDrawCount;
    const FLOAT blendFactor[4] = {};
    for (std::uint32_t drawIndex = firstDraw; drawIndex < endDraw; ++drawIndex)
    {
        const EndfieldVFXPeakDrawPayload& draw =
            g_EndfieldVFXPeakDraws[drawIndex];
        if (draw.textureIndex >= g_EndfieldVFXPeakTextureCount ||
            g_vfxPeakTextureViews[draw.textureIndex] == nullptr)
        {
            result = E_INVALIDARG;
            break;
        }
        ID3D11Buffer* vertexBuffers[2] = {
            g_vfxPeakVertexBuffers[drawIndex], g_vfxPeakSecondaryBuffer,
        };
        const UINT strides[2] = {g_EndfieldVFXPeakVertexStride, 0u};
        const UINT offsets[2] = {};
        ID3D11ShaderResourceView* pixelViews[2] = {
            depthView, g_vfxPeakTextureViews[draw.textureIndex],
        };
        context->IASetInputLayout(g_m14InputLayout);
        context->IASetVertexBuffers(0, 2, vertexBuffers, strides, offsets);
        context->IASetIndexBuffer(
            g_vfxPeakIndexBuffers[drawIndex], DXGI_FORMAT_R16_UINT, 0);
        context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
        context->VSSetShader(g_m14RuntimeVertexShader, nullptr, 0);
        context->PSSetShader(g_m14RuntimePixelShader, nullptr, 0);
        context->VSSetConstantBuffers(
            0, 5, g_vfxPeakVertexConstantBuffers[drawIndex]);
        context->PSSetConstantBuffers(
            0, 4, g_vfxPeakPixelConstantBuffers[drawIndex]);
        context->VSSetShaderResources(0, 1, &g_m14SkinView);
        context->PSSetShaderResources(0, 2, pixelViews);
        context->PSSetSamplers(0, 2, g_vfxPeakSamplers);
        context->OMSetBlendState(g_vfxPeakBlendState, blendFactor, 0xffffffffu);
        context->OMSetDepthStencilState(g_vfxPeakDepthState, 0);
        context->RSSetState(g_vfxPeakRasterizerState);
        context->DrawIndexed(draw.indexCount, 0, 0);
    }

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

    for (ID3D11SamplerState*& value : oldSamplers) ReleaseM14Object(value);
    for (ID3D11ShaderResourceView*& value : oldPixelViews)
        ReleaseM14Object(value);
    ReleaseM14Object(oldVertexView);
    for (ID3D11Buffer*& value : oldPixelCBs) ReleaseM14Object(value);
    for (ID3D11Buffer*& value : oldVertexCBs) ReleaseM14Object(value);
    ReleaseM14Object(oldRasterizerState);
    ReleaseM14Object(oldDepthState);
    ReleaseM14Object(oldBlendState);
    ReleaseM14Object(oldIndexBuffer);
    for (ID3D11Buffer*& value : oldVertexBuffers) ReleaseM14Object(value);
    ReleaseM14Object(oldInputLayout);
    ReleaseM14Object(oldPixelShader);
    ReleaseM14Object(oldVertexShader);
    ReleaseM14Object(renderDepth);
    ReleaseM14Object(renderTargets[1]);
    ReleaseM14Object(renderTargets[0]);
    ReleaseM14Object(depthView);
    context->Release();

    if (FAILED(result))
    {
        g_vfxPeakFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_vfxPeakLastResult.store(result, std::memory_order_relaxed);
        return;
    }
    g_vfxPeakDrawCount.fetch_add(
        endDraw - firstDraw, std::memory_order_relaxed);
    g_vfxPeakLastResult.store(S_OK, std::memory_order_relaxed);
}

void UNITY_INTERFACE_API DrawM29ExactRuntime(int eventId)
{
    if (eventId != 0)
        return;
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_m29FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m29LastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    HRESULT result = CreateM29RuntimeResources(device);
    if (FAILED(result))
    {
        ReleaseM29RuntimeResources();
        g_m29FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m29LastResult.store(result, std::memory_order_relaxed);
        return;
    }
    const std::uint32_t packetIndex =
        g_m29PacketIndex.load(std::memory_order_acquire);
    if (packetIndex >= g_EndfieldM29PacketCount)
    {
        g_m29FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m29LastResult.store(E_INVALIDARG, std::memory_order_relaxed);
        return;
    }

    ID3D11Resource* depthResource = reinterpret_cast<ID3D11Resource*>(
        g_m29DepthTexture.load(std::memory_order_acquire));
    ID3D11ShaderResourceView* depthView = nullptr;
    result = CreateDiagnosticShaderResourceView(device, depthResource, &depthView);
    if (FAILED(result) || depthView == nullptr ||
        g_m29TextureViews[0] == nullptr || g_m29TextureViews[1] == nullptr)
    {
        ReleaseM14Object(depthView);
        g_m29FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m29LastResult.store(
            FAILED(result) ? result : E_POINTER, std::memory_order_relaxed);
        return;
    }

    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        ReleaseM14Object(depthView);
        g_m29FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m29LastResult.store(E_POINTER, std::memory_order_relaxed);
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
        ReleaseM14Object(depthView);
        context->Release();
        g_m29FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m29LastResult.store(E_INVALIDARG, std::memory_order_relaxed);
        return;
    }

    ID3D11VertexShader* oldVertexShader = nullptr;
    ID3D11PixelShader* oldPixelShader = nullptr;
    ID3D11InputLayout* oldInputLayout = nullptr;
    ID3D11Buffer* oldVertexBuffers[2] = {};
    ID3D11Buffer* oldIndexBuffer = nullptr;
    ID3D11Buffer* oldVertexCBs[kM29VSConstantBufferCount] = {};
    ID3D11Buffer* oldPixelCBs[kM29PSConstantBufferCount] = {};
    ID3D11ShaderResourceView* oldVertexView = nullptr;
    ID3D11ShaderResourceView* oldPixelViews[3] = {};
    ID3D11SamplerState* oldSamplers[3] = {};
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
    context->VSGetConstantBuffers(
        0, static_cast<UINT>(kM29VSConstantBufferCount), oldVertexCBs);
    context->PSGetConstantBuffers(
        0, static_cast<UINT>(kM29PSConstantBufferCount), oldPixelCBs);
    context->VSGetShaderResources(0, 1, &oldVertexView);
    context->PSGetShaderResources(0, 3, oldPixelViews);
    context->PSGetSamplers(0, 3, oldSamplers);
    context->OMGetBlendState(&oldBlendState, oldBlendFactor, &oldSampleMask);
    context->OMGetDepthStencilState(&oldDepthState, &oldStencilReference);
    context->RSGetState(&oldRasterizerState);

    const EndfieldM29PacketPayload& packet = g_EndfieldM29Packets[packetIndex];
    const std::size_t layoutIndex = packet.vertexStride == 60u ? 0u : 1u;
    ID3D11Buffer* vertexBuffers[2] = {
        g_m29VertexBuffers[packetIndex], g_m29SecondaryBuffers[packetIndex],
    };
    const UINT strides[2] = {packet.vertexStride, 0u};
    const UINT offsets[2] = {};
    // Retail binds the unique 256x256 texture at t0 and aliases its shared
    // 512x512 texture at both t1 and t2.
    ID3D11ShaderResourceView* pixelViews[3] = {
        g_m29TextureViews[0], g_m29TextureViews[1], g_m29TextureViews[1],
    };
    const FLOAT blendFactor[4] = {};
    context->IASetInputLayout(g_m29InputLayouts[layoutIndex]);
    context->IASetVertexBuffers(0, 2, vertexBuffers, strides, offsets);
    context->IASetIndexBuffer(
        g_m29IndexBuffers[packetIndex], DXGI_FORMAT_R16_UINT, 0);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_m29RuntimeVertexShader, nullptr, 0);
    context->PSSetShader(g_m29RuntimePixelShader, nullptr, 0);
    context->VSSetConstantBuffers(
        0, static_cast<UINT>(kM29VSConstantBufferCount),
        g_m29VertexConstantBuffers[packetIndex]);
    context->PSSetConstantBuffers(
        0, static_cast<UINT>(kM29PSConstantBufferCount),
        g_m29PixelConstantBuffers[packetIndex]);
    context->VSSetShaderResources(0, 1, &g_m29SkinView);
    context->PSSetShaderResources(0, 3, pixelViews);
    context->PSSetSamplers(0, 3, g_m29Samplers);
    context->OMSetBlendState(g_m29BlendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(g_m29DepthState, 0);
    context->RSSetState(g_m29RasterizerState);
    context->DrawIndexed(packet.indexCount, 0, 0);

    ID3D11ShaderResourceView* nullVertexView = nullptr;
    ID3D11ShaderResourceView* nullPixelViews[3] = {};
    context->VSSetShaderResources(0, 1, &nullVertexView);
    context->PSSetShaderResources(0, 3, nullPixelViews);
    context->IASetInputLayout(oldInputLayout);
    context->IASetVertexBuffers(
        0, 2, oldVertexBuffers, oldVertexStrides, oldVertexOffsets);
    context->IASetIndexBuffer(oldIndexBuffer, oldIndexFormat, oldIndexOffset);
    context->IASetPrimitiveTopology(oldTopology);
    context->VSSetShader(oldVertexShader, nullptr, 0);
    context->PSSetShader(oldPixelShader, nullptr, 0);
    context->VSSetConstantBuffers(
        0, static_cast<UINT>(kM29VSConstantBufferCount), oldVertexCBs);
    context->PSSetConstantBuffers(
        0, static_cast<UINT>(kM29PSConstantBufferCount), oldPixelCBs);
    context->VSSetShaderResources(0, 1, &oldVertexView);
    context->PSSetShaderResources(0, 3, oldPixelViews);
    context->PSSetSamplers(0, 3, oldSamplers);
    context->OMSetBlendState(oldBlendState, oldBlendFactor, oldSampleMask);
    context->OMSetDepthStencilState(oldDepthState, oldStencilReference);
    context->RSSetState(oldRasterizerState);

    for (ID3D11SamplerState*& value : oldSamplers) ReleaseM14Object(value);
    for (ID3D11ShaderResourceView*& value : oldPixelViews)
        ReleaseM14Object(value);
    ReleaseM14Object(oldVertexView);
    for (ID3D11Buffer*& value : oldPixelCBs) ReleaseM14Object(value);
    for (ID3D11Buffer*& value : oldVertexCBs) ReleaseM14Object(value);
    ReleaseM14Object(oldRasterizerState);
    ReleaseM14Object(oldDepthState);
    ReleaseM14Object(oldBlendState);
    ReleaseM14Object(oldIndexBuffer);
    for (ID3D11Buffer*& value : oldVertexBuffers) ReleaseM14Object(value);
    ReleaseM14Object(oldInputLayout);
    ReleaseM14Object(oldPixelShader);
    ReleaseM14Object(oldVertexShader);
    ReleaseM14Object(renderDepth);
    ReleaseM14Object(renderTargets[1]);
    ReleaseM14Object(renderTargets[0]);
    ReleaseM14Object(depthView);
    context->Release();

    g_m29DrawCount.fetch_add(1, std::memory_order_relaxed);
    g_m29LastResult.store(S_OK, std::memory_order_relaxed);
}

void UNITY_INTERFACE_API DrawM30ExactRuntime(int eventId)
{
    if (eventId != 0)
        return;
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_m30FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m30LastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    HRESULT result = CreateM14RuntimeResources(device);
    if (FAILED(result))
    {
        ReleaseM14RuntimeResources();
        g_m30FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m30LastResult.store(result, std::memory_order_relaxed);
        return;
    }
    const std::uint32_t packetIndex =
        g_m30PacketIndex.load(std::memory_order_acquire);
    if (packetIndex >= g_EndfieldM30PacketCount)
    {
        g_m30FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m30LastResult.store(E_INVALIDARG, std::memory_order_relaxed);
        return;
    }

    ID3D11Resource* depthResource = reinterpret_cast<ID3D11Resource*>(
        g_m30DepthTexture.load(std::memory_order_acquire));
    ID3D11ShaderResourceView* depthView = nullptr;
    result = CreateDiagnosticShaderResourceView(device, depthResource, &depthView);
    if (FAILED(result) || depthView == nullptr || g_m30MainView == nullptr)
    {
        ReleaseM14Object(depthView);
        g_m30FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m30LastResult.store(
            FAILED(result) ? result : E_POINTER, std::memory_order_relaxed);
        return;
    }

    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        ReleaseM14Object(depthView);
        g_m30FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m30LastResult.store(E_POINTER, std::memory_order_relaxed);
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
        ReleaseM14Object(depthView);
        context->Release();
        g_m30FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m30LastResult.store(E_INVALIDARG, std::memory_order_relaxed);
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

    const EndfieldM30PacketPayload& packet = g_EndfieldM30Packets[packetIndex];
    ID3D11Buffer* vertexBuffers[2] = {
        g_m30VertexBuffers[packetIndex], g_m30SecondaryBuffers[packetIndex],
    };
    const UINT strides[2] = {g_EndfieldM30VertexStride, 0u};
    const UINT offsets[2] = {};
    ID3D11ShaderResourceView* pixelViews[2] = {depthView, g_m30MainView};
    const FLOAT blendFactor[4] = {};
    context->IASetInputLayout(g_m14InputLayout);
    context->IASetVertexBuffers(0, 2, vertexBuffers, strides, offsets);
    context->IASetIndexBuffer(
        g_m30IndexBuffers[packetIndex], DXGI_FORMAT_R16_UINT, 0);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_m14RuntimeVertexShader, nullptr, 0);
    context->PSSetShader(g_m14RuntimePixelShader, nullptr, 0);
    context->VSSetConstantBuffers(0, 5, g_m30VertexConstantBuffers[packetIndex]);
    context->PSSetConstantBuffers(0, 4, g_m30PixelConstantBuffers[packetIndex]);
    context->VSSetShaderResources(0, 1, &g_m14SkinView);
    context->PSSetShaderResources(0, 2, pixelViews);
    context->PSSetSamplers(0, 2, g_m14Samplers);
    context->OMSetBlendState(g_m14BlendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(g_m14DepthState, 0);
    context->RSSetState(g_m14RasterizerState);
    context->DrawIndexed(packet.indexCount, 0, 0);

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

    for (ID3D11SamplerState*& value : oldSamplers) ReleaseM14Object(value);
    for (ID3D11ShaderResourceView*& value : oldPixelViews) ReleaseM14Object(value);
    ReleaseM14Object(oldVertexView);
    for (ID3D11Buffer*& value : oldPixelCBs) ReleaseM14Object(value);
    for (ID3D11Buffer*& value : oldVertexCBs) ReleaseM14Object(value);
    ReleaseM14Object(oldRasterizerState);
    ReleaseM14Object(oldDepthState);
    ReleaseM14Object(oldBlendState);
    ReleaseM14Object(oldIndexBuffer);
    for (ID3D11Buffer*& value : oldVertexBuffers) ReleaseM14Object(value);
    ReleaseM14Object(oldInputLayout);
    ReleaseM14Object(oldPixelShader);
    ReleaseM14Object(oldVertexShader);
    ReleaseM14Object(renderDepth);
    ReleaseM14Object(renderTargets[1]);
    ReleaseM14Object(renderTargets[0]);
    ReleaseM14Object(depthView);
    context->Release();

    g_m30DrawCount.fetch_add(1, std::memory_order_relaxed);
    g_m30LastResult.store(S_OK, std::memory_order_relaxed);
}

void UNITY_INTERFACE_API DrawOpeningStripExactRuntime(int eventId)
{
    if (eventId != 0) return;
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_openingStripFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_openingStripLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    HRESULT result = CreateOpeningStripResources(device);
    if (FAILED(result))
    {
        ReleaseOpeningStripResources();
        g_openingStripFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_openingStripLastResult.store(result, std::memory_order_relaxed);
        return;
    }
    std::uint32_t outputWidth = 0;
    std::uint32_t outputHeight = 0;
    UnpackOpeningStripDimensions(
        g_openingStripOutputDimensions.load(std::memory_order_acquire),
        outputWidth,
        outputHeight);
    if (g_openingStripScreenSizePatched.load(std::memory_order_acquire) != 1u ||
        outputWidth != g_openingStripResourceWidth ||
        outputHeight != g_openingStripResourceHeight)
    {
        g_openingStripFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_openingStripLastResult.store(E_FAIL, std::memory_order_relaxed);
        return;
    }
    ID3D11Resource* sceneColor = reinterpret_cast<ID3D11Resource*>(
        g_openingStripSceneColor.load(std::memory_order_acquire));
    if (g_openingStripMaskView == nullptr || sceneColor == nullptr)
    {
        g_openingStripFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_openingStripLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        g_openingStripFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_openingStripLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    ID3D11RenderTargetView* targets[2] = {};
    ID3D11DepthStencilView* renderDepth = nullptr;
    context->OMGetRenderTargets(2, targets, &renderDepth);
    ID3D11Resource* output = nullptr;
    if (targets[0] != nullptr) targets[0]->GetResource(&output);
    if (targets[0] == nullptr || targets[1] == nullptr || renderDepth == nullptr ||
        output == sceneColor)
    {
        ReleaseM14Object(output);
        ReleaseM14Object(renderDepth);
        ReleaseM14Object(targets[1]);
        ReleaseM14Object(targets[0]);
        context->Release();
        g_openingStripFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_openingStripLastResult.store(E_INVALIDARG, std::memory_order_relaxed);
        return;
    }
    ID3D11Texture2D* outputTexture = nullptr;
    ID3D11Texture2D* sceneColorTexture = nullptr;
    D3D11_TEXTURE2D_DESC outputDescription = {};
    D3D11_TEXTURE2D_DESC sceneColorDescription = {};
    const HRESULT outputTextureResult = output->QueryInterface(
        __uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&outputTexture));
    const HRESULT sceneColorTextureResult = sceneColor->QueryInterface(
        __uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&sceneColorTexture));
    if (SUCCEEDED(outputTextureResult) && outputTexture != nullptr)
        outputTexture->GetDesc(&outputDescription);
    if (SUCCEEDED(sceneColorTextureResult) && sceneColorTexture != nullptr)
        sceneColorTexture->GetDesc(&sceneColorDescription);
    const bool dimensionsMatch =
        SUCCEEDED(outputTextureResult) && SUCCEEDED(sceneColorTextureResult) &&
        outputTexture != nullptr && sceneColorTexture != nullptr &&
        outputDescription.Width == outputWidth &&
        outputDescription.Height == outputHeight &&
        sceneColorDescription.Width == outputWidth &&
        sceneColorDescription.Height == outputHeight;
    ReleaseM14Object(sceneColorTexture);
    ReleaseM14Object(outputTexture);
    if (!dimensionsMatch)
    {
        ReleaseM14Object(output);
        ReleaseM14Object(renderDepth);
        ReleaseM14Object(targets[1]);
        ReleaseM14Object(targets[0]);
        context->Release();
        g_openingStripFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_openingStripLastResult.store(E_INVALIDARG, std::memory_order_relaxed);
        return;
    }
    ID3D11ShaderResourceView* views[2] = {};
    views[0] = g_openingStripMaskView;
    views[0]->AddRef();
    result = CreateDiagnosticShaderResourceView(device, sceneColor, &views[1]);
    if (FAILED(result) || views[1] == nullptr)
    {
        ReleaseM14Object(views[1]); ReleaseM14Object(views[0]);
        ReleaseM14Object(output); ReleaseM14Object(renderDepth);
        ReleaseM14Object(targets[1]); ReleaseM14Object(targets[0]);
        context->Release();
        g_openingStripFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_openingStripLastResult.store(FAILED(result) ? result : E_POINTER,
            std::memory_order_relaxed);
        return;
    }

    ID3D11VertexShader* oldVS = nullptr; ID3D11PixelShader* oldPS = nullptr;
    ID3D11InputLayout* oldLayout = nullptr; ID3D11Buffer* oldVBs[2] = {};
    ID3D11Buffer* oldIB = nullptr; ID3D11Buffer* oldVSCBs[5] = {};
    ID3D11Buffer* oldPSCBs[4] = {}; ID3D11ShaderResourceView* oldVSView = nullptr;
    ID3D11ShaderResourceView* oldPSViews[2] = {}; ID3D11SamplerState* oldSamplers[2] = {};
    ID3D11BlendState* oldBlend = nullptr; ID3D11DepthStencilState* oldDepth = nullptr;
    ID3D11RasterizerState* oldRasterizer = nullptr;
    D3D11_VIEWPORT oldViewports[D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    UINT oldViewportCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_RECT oldScissors[D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    UINT oldScissorCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_PRIMITIVE_TOPOLOGY oldTopology = D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    DXGI_FORMAT oldIndexFormat = DXGI_FORMAT_UNKNOWN; UINT oldStrides[2] = {};
    UINT oldOffsets[2] = {}; UINT oldIndexOffset = 0; FLOAT oldBlendFactor[4] = {};
    UINT oldSampleMask = 0; UINT oldStencilReference = 0;
    context->VSGetShader(&oldVS, nullptr, nullptr); context->PSGetShader(&oldPS, nullptr, nullptr);
    context->IAGetInputLayout(&oldLayout);
    context->IAGetVertexBuffers(0, 2, oldVBs, oldStrides, oldOffsets);
    context->IAGetIndexBuffer(&oldIB, &oldIndexFormat, &oldIndexOffset);
    context->IAGetPrimitiveTopology(&oldTopology);
    context->VSGetConstantBuffers(0, 5, oldVSCBs);
    context->PSGetConstantBuffers(0, 4, oldPSCBs);
    context->VSGetShaderResources(0, 1, &oldVSView);
    context->PSGetShaderResources(0, 2, oldPSViews);
    context->PSGetSamplers(0, 2, oldSamplers);
    context->OMGetBlendState(&oldBlend, oldBlendFactor, &oldSampleMask);
    context->OMGetDepthStencilState(&oldDepth, &oldStencilReference);
    context->RSGetState(&oldRasterizer);
    context->RSGetViewports(&oldViewportCount, oldViewports);
    context->RSGetScissorRects(&oldScissorCount, oldScissors);

    const std::uint32_t packet = g_openingStripPacketIndex.load(std::memory_order_acquire);
    const EndfieldOpeningStripPacket& source = g_EndfieldOpeningStripPackets[packet];
    ID3D11Buffer* vertexBuffers[2] = {
        g_openingStripVertexBuffers[packet], g_openingStripDefaultVertexBuffer};
    const UINT strides[2] = {g_EndfieldOpeningStripVertexStride, 0u};
    const UINT offsets[2] = {}; const FLOAT blendFactor[4] = {1, 1, 1, 1};
    const D3D11_VIEWPORT viewport = {
        0.0f, 0.0f,
        static_cast<FLOAT>(outputWidth), static_cast<FLOAT>(outputHeight),
        0.0f, 1.0f};
    const D3D11_RECT scissor = {
        0, 0, static_cast<LONG>(outputWidth), static_cast<LONG>(outputHeight)};
    context->IASetInputLayout(g_openingStripInputLayout);
    context->IASetVertexBuffers(0, 2, vertexBuffers, strides, offsets);
    context->IASetIndexBuffer(g_openingStripIndexBuffers[packet], DXGI_FORMAT_R16_UINT, 0);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_openingStripVertexShader, nullptr, 0);
    context->PSSetShader(g_openingStripPixelShader, nullptr, 0);
    context->VSSetConstantBuffers(0, 5, g_openingStripVertexConstantBuffers[packet]);
    context->PSSetConstantBuffers(0, 4, g_openingStripPixelConstantBuffers[packet]);
    context->VSSetShaderResources(0, 1, &g_openingStripSkinView);
    context->PSSetShaderResources(0, 2, views);
    context->PSSetSamplers(0, 2, g_openingStripSamplers);
    context->OMSetBlendState(g_openingStripBlendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(g_openingStripDepthState, 0);
    context->RSSetState(g_openingStripRasterizerState);
    context->RSSetViewports(1, &viewport);
    context->RSSetScissorRects(1, &scissor);
    context->DrawIndexed(source.indexCount, 0, 0);

    ID3D11ShaderResourceView* nullVS = nullptr; ID3D11ShaderResourceView* nullPS[2] = {};
    context->VSSetShaderResources(0, 1, &nullVS); context->PSSetShaderResources(0, 2, nullPS);
    context->IASetInputLayout(oldLayout);
    context->IASetVertexBuffers(0, 2, oldVBs, oldStrides, oldOffsets);
    context->IASetIndexBuffer(oldIB, oldIndexFormat, oldIndexOffset);
    context->IASetPrimitiveTopology(oldTopology);
    context->VSSetShader(oldVS, nullptr, 0); context->PSSetShader(oldPS, nullptr, 0);
    context->VSSetConstantBuffers(0, 5, oldVSCBs);
    context->PSSetConstantBuffers(0, 4, oldPSCBs);
    context->VSSetShaderResources(0, 1, &oldVSView);
    context->PSSetShaderResources(0, 2, oldPSViews);
    context->PSSetSamplers(0, 2, oldSamplers);
    context->OMSetBlendState(oldBlend, oldBlendFactor, oldSampleMask);
    context->OMSetDepthStencilState(oldDepth, oldStencilReference);
    context->RSSetState(oldRasterizer);
    context->RSSetViewports(oldViewportCount, oldViewports);
    context->RSSetScissorRects(oldScissorCount, oldScissors);
    for (ID3D11SamplerState*& value : oldSamplers) ReleaseM14Object(value);
    for (ID3D11ShaderResourceView*& value : oldPSViews) ReleaseM14Object(value);
    ReleaseM14Object(oldVSView);
    for (ID3D11Buffer*& value : oldPSCBs) ReleaseM14Object(value);
    for (ID3D11Buffer*& value : oldVSCBs) ReleaseM14Object(value);
    ReleaseM14Object(oldRasterizer); ReleaseM14Object(oldDepth); ReleaseM14Object(oldBlend);
    ReleaseM14Object(oldIB); for (ID3D11Buffer*& value : oldVBs) ReleaseM14Object(value);
    ReleaseM14Object(oldLayout); ReleaseM14Object(oldPS); ReleaseM14Object(oldVS);
    ReleaseM14Object(views[1]); ReleaseM14Object(views[0]); ReleaseM14Object(output);
    ReleaseM14Object(renderDepth); ReleaseM14Object(targets[1]); ReleaseM14Object(targets[0]);
    context->Release();
    g_openingStripDrawCount.fetch_add(1, std::memory_order_relaxed);
    g_openingStripLastResult.store(S_OK, std::memory_order_relaxed);
}

void UNITY_INTERFACE_API DrawM13ExactRuntime(int eventId)
{
    if (eventId != 0)
        return;
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_m13FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m13LastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    HRESULT result = CreateM13RuntimeResources(device);
    if (SUCCEEDED(result))
        result = EnsureM13ScreenConstantBuffers(device);
    if (FAILED(result))
    {
        ReleaseM13RuntimeResources();
        g_m13FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m13LastResult.store(result, std::memory_order_relaxed);
        return;
    }
    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        g_m13FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m13LastResult.store(E_POINTER, std::memory_order_relaxed);
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
        context->Release();
        g_m13FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m13LastResult.store(E_INVALIDARG, std::memory_order_relaxed);
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
    ID3D11ShaderResourceView* oldPixelViews[5] = {};
    ID3D11SamplerState* oldSamplers[5] = {};
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
    context->PSGetShaderResources(0, 5, oldPixelViews);
    context->PSGetSamplers(0, 5, oldSamplers);
    context->OMGetBlendState(&oldBlendState, oldBlendFactor, &oldSampleMask);
    context->OMGetDepthStencilState(&oldDepthState, &oldStencilReference);
    context->RSGetState(&oldRasterizerState);
    UINT oldViewportCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_VIEWPORT oldViewports[D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    context->RSGetViewports(&oldViewportCount, oldViewports);
    UINT oldScissorCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_RECT oldScissors[D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    context->RSGetScissorRects(&oldScissorCount, oldScissors);

    const std::uint32_t packetIndex =
        g_m13PacketIndex.load(std::memory_order_acquire);
    ID3D11Buffer* vertexBuffers[2] = {
        g_m13VertexBuffers[packetIndex],
        g_m13DefaultVertexBuffer,
    };
    const UINT strides[2] = {g_EndfieldM13VertexStride, 0};
    const UINT offsets[2] = {};
    const FLOAT blendFactor[4] = {};
    context->IASetInputLayout(g_m13InputLayout);
    context->IASetVertexBuffers(0, 2, vertexBuffers, strides, offsets);
    context->IASetIndexBuffer(g_m13IndexBuffer, DXGI_FORMAT_R16_UINT, 0);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_m13RuntimeVertexShader, nullptr, 0);
    context->PSSetShader(g_m13RuntimePixelShader, nullptr, 0);
    context->VSSetConstantBuffers(
        0, 5, g_m13VertexConstantBuffers[packetIndex]);
    context->PSSetConstantBuffers(
        0, 4, g_m13PixelConstantBuffers[packetIndex]);
    context->VSSetShaderResources(0, 1, &g_m13SkinView);
    context->PSSetShaderResources(0, 5, g_m13TextureViews);
    context->PSSetSamplers(0, 5, g_m13Samplers);
    context->OMSetBlendState(g_m13BlendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(g_m13DepthState, 0);
    context->RSSetState(g_m13RasterizerState);
    const D3D11_VIEWPORT viewport = {
        0.0f, 0.0f, static_cast<float>(g_m13ResourceWidth),
        static_cast<float>(g_m13ResourceHeight), 0.0f, 1.0f};
    const D3D11_RECT scissor = {
        0, 0, static_cast<LONG>(g_m13ResourceWidth),
        static_cast<LONG>(g_m13ResourceHeight)};
    context->RSSetViewports(1, &viewport);
    context->RSSetScissorRects(1, &scissor);
    context->DrawIndexed(6, 0, 0);

    ID3D11ShaderResourceView* nullVertexView = nullptr;
    ID3D11ShaderResourceView* nullPixelViews[5] = {};
    context->VSSetShaderResources(0, 1, &nullVertexView);
    context->PSSetShaderResources(0, 5, nullPixelViews);
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
    context->PSSetShaderResources(0, 5, oldPixelViews);
    context->PSSetSamplers(0, 5, oldSamplers);
    context->OMSetBlendState(oldBlendState, oldBlendFactor, oldSampleMask);
    context->OMSetDepthStencilState(oldDepthState, oldStencilReference);
    context->RSSetState(oldRasterizerState);
    context->RSSetViewports(oldViewportCount, oldViewports);
    context->RSSetScissorRects(oldScissorCount, oldScissors);

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
    context->Release();
    g_m13DrawCount.fetch_add(1, std::memory_order_relaxed);
    g_m13LastResult.store(S_OK, std::memory_order_relaxed);
}

void RecordEndminfUberFailure(HRESULT result, std::uint32_t stage)
{
    g_endminfUberFailureStage.store(stage, std::memory_order_relaxed);
    g_endminfUberLastResult.store(result, std::memory_order_relaxed);
    g_endminfUberFailureCount.fetch_add(1, std::memory_order_relaxed);
}

void ReleaseEndminfUberPacketTextures(EndminfUberPacket& packet)
{
    for (ID3D11Texture2D*& texture : packet.textures)
        ReleaseM14Object(texture);
}

void ReleaseEndminfUberRuntimeResources()
{
    ReleaseM14Object(g_endminfUberOutputDepthView);
    ReleaseM14Object(g_endminfUberOutputDepthTexture);
    ReleaseM14Object(g_endminfUberRasterizerState);
    ReleaseM14Object(g_endminfUberDepthState);
    ReleaseM14Object(g_endminfUberBlendState);
    ReleaseM14Object(g_endminfUberSampler);
    ReleaseM14Object(g_endminfUberPixelShader);
    ReleaseM14Object(g_endminfUberNormalPixelShader);
    ReleaseM14Object(g_endminfUberVertexShader);
    std::lock_guard<std::mutex> lock(g_endminfUberMutex);
    for (ID3D11Texture2D*& texture : g_endminfUberConfiguredTextures)
        ReleaseM14Object(texture);
    for (EndminfUberPacket& packet : g_endminfUberPackets)
    {
        ReleaseEndminfUberPacketTextures(packet);
        packet.eventId.store(0u, std::memory_order_relaxed);
        packet.state.store(EndminfUberPacketState::Empty,
            std::memory_order_release);
    }
    g_endminfUberNextEventId = 1;
}

bool IsEndminfUberTexture(
    ID3D11Texture2D* texture,
    DXGI_FORMAT format,
    UINT width,
    UINT height)
{
    if (texture == nullptr)
        return false;
    D3D11_TEXTURE2D_DESC description = {};
    texture->GetDesc(&description);
    const bool compatibleFormat = description.Format == format ||
        (format == DXGI_FORMAT_R16G16B16A16_FLOAT &&
         description.Format == DXGI_FORMAT_R16G16B16A16_TYPELESS);
    return description.Width == width && description.Height == height &&
        description.MipLevels >= 1u && description.ArraySize == 1u &&
        compatibleFormat && description.SampleDesc.Count == 1u &&
        (description.BindFlags & D3D11_BIND_SHADER_RESOURCE) != 0u;
}

bool ValidateEndminfUberTextureSet(
    ID3D11Texture2D* const textures[3],
    UINT width,
    UINT height)
{
    if (width == 0u || height == 0u)
        return false;
    return IsEndminfUberTexture(
               textures[0], DXGI_FORMAT_R16G16B16A16_FLOAT, width, height) &&
        IsEndminfUberTexture(
            textures[1], DXGI_FORMAT_R11G11B10_FLOAT,
            (width + 1u) / 2u, (height + 1u) / 2u) &&
        IsEndminfUberTexture(
            textures[2], DXGI_FORMAT_R16G16B16A16_FLOAT, 1024u, 32u);
}

HRESULT CreateEndminfUberRuntimeResources(ID3D11Device* device)
{
    if (device == nullptr)
        return E_POINTER;
    if (g_endminfUberVertexShader != nullptr &&
        g_endminfUberNormalPixelShader != nullptr &&
        g_endminfUberPixelShader != nullptr &&
        g_endminfUberSampler != nullptr &&
        g_endminfUberBlendState != nullptr &&
        g_endminfUberDepthState != nullptr &&
        g_endminfUberRasterizerState != nullptr)
    {
        return S_OK;
    }

    ReleaseM14Object(g_endminfUberRasterizerState);
    ReleaseM14Object(g_endminfUberDepthState);
    ReleaseM14Object(g_endminfUberBlendState);
    ReleaseM14Object(g_endminfUberSampler);
    ReleaseM14Object(g_endminfUberPixelShader);
    ReleaseM14Object(g_endminfUberNormalPixelShader);
    ReleaseM14Object(g_endminfUberVertexShader);

    g_endminfUberFailureStage.store(101u, std::memory_order_relaxed);
    HRESULT result = device->CreateVertexShader(
        g_EndfieldUberVertexDxbc,
        g_EndfieldUberVertexDxbcSize,
        nullptr,
        &g_endminfUberVertexShader);
    if (FAILED(result))
        return result;
    g_endminfUberFailureStage.store(102u, std::memory_order_relaxed);
    result = device->CreatePixelShader(
        g_EndfieldUberNormalPixelDxbc,
        g_EndfieldUberNormalPixelDxbcSize,
        nullptr,
        &g_endminfUberNormalPixelShader);
    if (FAILED(result))
        return result;
    g_endminfUberFailureStage.store(103u, std::memory_order_relaxed);
    result = device->CreatePixelShader(
        g_EndfieldUberPixelDxbc,
        g_EndfieldUberPixelDxbcSize,
        nullptr,
        &g_endminfUberPixelShader);
    if (FAILED(result))
        return result;

    D3D11_SAMPLER_DESC sampler = {};
    sampler.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    sampler.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.MinLOD = 0.0f;
    sampler.MaxLOD = D3D11_FLOAT32_MAX;
    g_endminfUberFailureStage.store(104u, std::memory_order_relaxed);
    result = device->CreateSamplerState(&sampler, &g_endminfUberSampler);
    if (FAILED(result))
        return result;

    D3D11_BLEND_DESC blend = {};
    blend.RenderTarget[0].BlendEnable = FALSE;
    blend.RenderTarget[0].RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
    g_endminfUberFailureStage.store(105u, std::memory_order_relaxed);
    result = device->CreateBlendState(&blend, &g_endminfUberBlendState);
    if (FAILED(result))
        return result;

    D3D11_DEPTH_STENCIL_DESC depth = {};
    depth.DepthEnable = FALSE;
    depth.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
    depth.DepthFunc = D3D11_COMPARISON_ALWAYS;
    depth.StencilEnable = FALSE;
    g_endminfUberFailureStage.store(106u, std::memory_order_relaxed);
    result = device->CreateDepthStencilState(&depth, &g_endminfUberDepthState);
    if (FAILED(result))
        return result;

    D3D11_RASTERIZER_DESC rasterizer = {};
    rasterizer.FillMode = D3D11_FILL_SOLID;
    rasterizer.CullMode = D3D11_CULL_NONE;
    rasterizer.DepthClipEnable = TRUE;
    rasterizer.ScissorEnable = TRUE;
    g_endminfUberFailureStage.store(107u, std::memory_order_relaxed);
    result = device->CreateRasterizerState(
        &rasterizer, &g_endminfUberRasterizerState);
    if (SUCCEEDED(result))
        g_endminfUberFailureStage.store(0u, std::memory_order_relaxed);
    return result;
}

HRESULT EnsureEndminfUberOutputDepth(
    ID3D11Device* device,
    UINT width,
    UINT height)
{
    if (device == nullptr || width == 0u || height == 0u)
        return E_INVALIDARG;
    if (g_endminfUberOutputDepthTexture != nullptr &&
        g_endminfUberOutputDepthView != nullptr)
    {
        D3D11_TEXTURE2D_DESC existing = {};
        g_endminfUberOutputDepthTexture->GetDesc(&existing);
        if (existing.Width == width && existing.Height == height &&
            existing.Format == DXGI_FORMAT_R24G8_TYPELESS &&
            existing.SampleDesc.Count == 1u)
        {
            return S_OK;
        }
    }

    ReleaseM14Object(g_endminfUberOutputDepthView);
    ReleaseM14Object(g_endminfUberOutputDepthTexture);
    D3D11_TEXTURE2D_DESC texture = {};
    texture.Width = width;
    texture.Height = height;
    texture.MipLevels = 1u;
    texture.ArraySize = 1u;
    texture.Format = DXGI_FORMAT_R24G8_TYPELESS;
    texture.SampleDesc.Count = 1u;
    texture.Usage = D3D11_USAGE_DEFAULT;
    texture.BindFlags = D3D11_BIND_DEPTH_STENCIL;
    g_endminfUberFailureStage.store(108u, std::memory_order_relaxed);
    HRESULT result = device->CreateTexture2D(
        &texture, nullptr, &g_endminfUberOutputDepthTexture);
    if (FAILED(result))
        return result;

    D3D11_DEPTH_STENCIL_VIEW_DESC view = {};
    view.Format = DXGI_FORMAT_D24_UNORM_S8_UINT;
    view.ViewDimension = D3D11_DSV_DIMENSION_TEXTURE2D;
    view.Texture2D.MipSlice = 0u;
    g_endminfUberFailureStage.store(109u, std::memory_order_relaxed);
    result = device->CreateDepthStencilView(
        g_endminfUberOutputDepthTexture,
        &view,
        &g_endminfUberOutputDepthView);
    if (FAILED(result))
    {
        ReleaseM14Object(g_endminfUberOutputDepthTexture);
        return result;
    }
    g_endminfUberFailureStage.store(0u, std::memory_order_relaxed);
    return S_OK;
}

void PatchEndminfUberFloat(
    std::uint8_t* bytes,
    std::size_t byteCount,
    std::size_t floatIndex,
    float value)
{
    const std::size_t offset = floatIndex * sizeof(float);
    if (bytes != nullptr && offset + sizeof(float) <= byteCount)
        std::memcpy(bytes + offset, &value, sizeof(value));
}

bool EndminfUberEventIdInUse(std::uint32_t eventId)
{
    for (const EndminfUberPacket& packet : g_endminfUberPackets)
    {
        if (packet.state.load(std::memory_order_acquire) !=
                EndminfUberPacketState::Empty &&
            packet.eventId.load(std::memory_order_relaxed) == eventId)
        {
            return true;
        }
    }
    return false;
}

std::uint32_t AllocateEndminfUberEventId()
{
    for (std::size_t attempt = 0;
         attempt <= kEndminfUberPacketCapacity;
         ++attempt)
    {
        std::uint32_t candidate = g_endminfUberNextEventId++;
        if (candidate == 0u || candidate > kEndminfUberMaximumEventId)
        {
            candidate = 1u;
            g_endminfUberNextEventId = 2u;
        }
        if (!EndminfUberEventIdInUse(candidate))
            return candidate;
    }
    return 0u;
}

void ReleaseEndminfUberClassInstances(
    ID3D11ClassInstance** instances,
    UINT count)
{
    for (UINT index = 0; index < count; ++index)
        ReleaseM14Object(instances[index]);
}

void UNITY_INTERFACE_API DrawEndminfUberExactRuntime(int eventId)
{
    EndminfUberPacket* packet = nullptr;
    if (eventId > 0)
    {
        for (EndminfUberPacket& candidate : g_endminfUberPackets)
        {
            if (candidate.state.load(std::memory_order_acquire) !=
                EndminfUberPacketState::Ready)
            {
                continue;
            }
            if (candidate.eventId.load(std::memory_order_relaxed) !=
                static_cast<std::uint32_t>(eventId))
                continue;
            EndminfUberPacketState expected = EndminfUberPacketState::Ready;
            if (candidate.state.compare_exchange_strong(
                    expected,
                    EndminfUberPacketState::Consuming,
                    std::memory_order_acq_rel))
            {
                packet = &candidate;
            }
            break;
        }
    }
    if (packet == nullptr)
    {
        RecordEndminfUberFailure(E_INVALIDARG, 201u);
        return;
    }

    const auto finishPacket = [packet]() {
        ReleaseEndminfUberPacketTextures(*packet);
        packet->eventId.store(0u, std::memory_order_relaxed);
        packet->state.store(
            EndminfUberPacketState::Empty, std::memory_order_release);
    };

    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        RecordEndminfUberFailure(E_POINTER, 202u);
        finishPacket();
        return;
    }
    if (!ValidateEndminfUberTextureSet(
            packet->textures, packet->width, packet->height))
    {
        RecordEndminfUberFailure(E_INVALIDARG, 203u);
        finishPacket();
        return;
    }
    HRESULT result = CreateEndminfUberRuntimeResources(device);
    if (FAILED(result))
    {
        RecordEndminfUberFailure(result,
            g_endminfUberFailureStage.load(std::memory_order_relaxed));
        finishPacket();
        return;
    }
    result = EnsureEndminfUberOutputDepth(
        device, packet->width, packet->height);
    if (FAILED(result))
    {
        RecordEndminfUberFailure(result,
            g_endminfUberFailureStage.load(std::memory_order_relaxed));
        finishPacket();
        return;
    }

    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        RecordEndminfUberFailure(E_POINTER, 204u);
        finishPacket();
        return;
    }

    ID3D11RenderTargetView* renderTargets[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT] = {};
    ID3D11DepthStencilView* renderDepth = nullptr;
    context->OMGetRenderTargets(
        D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT, renderTargets, &renderDepth);
    bool targetReady = renderTargets[0] != nullptr;
    for (std::size_t index = 1;
         index < D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT;
         ++index)
    {
        targetReady = targetReady && renderTargets[index] == nullptr;
    }

    ID3D11Resource* outputResource = nullptr;
    ID3D11Texture2D* outputTexture = nullptr;
    D3D11_RENDER_TARGET_VIEW_DESC outputViewDescription = {};
    D3D11_TEXTURE2D_DESC outputDescription = {};
    D3D11_DEPTH_STENCIL_VIEW_DESC depthViewDescription = {};
    D3D11_TEXTURE2D_DESC depthDescription = {};
    if (targetReady)
    {
        renderTargets[0]->GetDesc(&outputViewDescription);
        renderTargets[0]->GetResource(&outputResource);
        if (outputResource == nullptr ||
            FAILED(outputResource->QueryInterface(
                __uuidof(ID3D11Texture2D),
                reinterpret_cast<void**>(&outputTexture))))
        {
            targetReady = false;
        }
    }
    if (targetReady)
    {
        outputTexture->GetDesc(&outputDescription);
        targetReady =
            outputViewDescription.Format == DXGI_FORMAT_R8G8B8A8_UNORM &&
            outputViewDescription.ViewDimension == D3D11_RTV_DIMENSION_TEXTURE2D &&
            outputViewDescription.Texture2D.MipSlice == 0u &&
            outputDescription.Width == packet->width &&
            outputDescription.Height == packet->height &&
            outputDescription.SampleDesc.Count == 1u &&
            outputDescription.ArraySize == 1u;
        for (ID3D11Texture2D* texture : packet->textures)
            targetReady = targetReady && texture != outputTexture;
    }
    if (targetReady)
    {
        g_endminfUberOutputDepthView->GetDesc(&depthViewDescription);
        g_endminfUberOutputDepthTexture->GetDesc(&depthDescription);
        targetReady =
            depthViewDescription.Format == DXGI_FORMAT_D24_UNORM_S8_UINT &&
            depthViewDescription.ViewDimension ==
                D3D11_DSV_DIMENSION_TEXTURE2D &&
            depthViewDescription.Texture2D.MipSlice == 0u &&
            depthDescription.Format == DXGI_FORMAT_R24G8_TYPELESS &&
            depthDescription.Width == packet->width &&
            depthDescription.Height == packet->height &&
            depthDescription.SampleDesc.Count == 1u &&
            depthDescription.ArraySize == 1u &&
            g_endminfUberOutputDepthTexture != outputTexture;
    }
    if (!targetReady)
    {
        ReleaseM14Object(outputTexture);
        ReleaseM14Object(outputResource);
        ReleaseM14Object(renderDepth);
        for (ID3D11RenderTargetView*& target : renderTargets)
            ReleaseM14Object(target);
        context->Release();
        RecordEndminfUberFailure(E_INVALIDARG, 205u);
        finishPacket();
        return;
    }

    ID3D11Buffer* vertexConstant = nullptr;
    ID3D11Buffer* pixelConstants[2] = {};
    ID3D11ShaderResourceView* resources[3] = {};
    result = CreateM14ImmutableBuffer(
        device, D3D11_BIND_CONSTANT_BUFFER,
        packet->vsB0, static_cast<UINT>(sizeof(packet->vsB0)),
        &vertexConstant);
    if (SUCCEEDED(result))
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_CONSTANT_BUFFER,
            packet->psB0, static_cast<UINT>(sizeof(packet->psB0)),
            &pixelConstants[0]);
    if (SUCCEEDED(result))
        result = CreateM14ImmutableBuffer(
            device, D3D11_BIND_CONSTANT_BUFFER,
            packet->psB1, static_cast<UINT>(sizeof(packet->psB1)),
            &pixelConstants[1]);
    std::uint32_t resourceFailureStage = 206u;
    for (std::size_t index = 0; SUCCEEDED(result) && index < 3; ++index)
    {
        D3D11_TEXTURE2D_DESC textureDescription = {};
        packet->textures[index]->GetDesc(&textureDescription);
        D3D11_SHADER_RESOURCE_VIEW_DESC viewDescription = {};
        viewDescription.Format = ShaderResourceFormat(textureDescription.Format);
        viewDescription.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
        viewDescription.Texture2D.MostDetailedMip = 0u;
        viewDescription.Texture2D.MipLevels = 1u;
        resourceFailureStage = 206u + static_cast<std::uint32_t>(index);
        result = device->CreateShaderResourceView(
            packet->textures[index], &viewDescription, &resources[index]);
    }
    if (FAILED(result))
    {
        for (ID3D11ShaderResourceView*& resource : resources)
            ReleaseM14Object(resource);
        for (ID3D11Buffer*& constant : pixelConstants)
            ReleaseM14Object(constant);
        ReleaseM14Object(vertexConstant);
        ReleaseM14Object(renderDepth);
        ReleaseM14Object(outputTexture);
        ReleaseM14Object(outputResource);
        for (ID3D11RenderTargetView*& target : renderTargets)
            ReleaseM14Object(target);
        context->Release();
        RecordEndminfUberFailure(result, resourceFailureStage);
        finishPacket();
        return;
    }

    constexpr UINT kClassCapacity = 256u;
    ID3D11VertexShader* oldVertexShader = nullptr;
    ID3D11PixelShader* oldPixelShader = nullptr;
    ID3D11GeometryShader* oldGeometryShader = nullptr;
    ID3D11HullShader* oldHullShader = nullptr;
    ID3D11DomainShader* oldDomainShader = nullptr;
    ID3D11ClassInstance* oldVertexClasses[kClassCapacity] = {};
    ID3D11ClassInstance* oldPixelClasses[kClassCapacity] = {};
    ID3D11ClassInstance* oldGeometryClasses[kClassCapacity] = {};
    ID3D11ClassInstance* oldHullClasses[kClassCapacity] = {};
    ID3D11ClassInstance* oldDomainClasses[kClassCapacity] = {};
    UINT oldVertexClassCount = kClassCapacity;
    UINT oldPixelClassCount = kClassCapacity;
    UINT oldGeometryClassCount = kClassCapacity;
    UINT oldHullClassCount = kClassCapacity;
    UINT oldDomainClassCount = kClassCapacity;
    ID3D11InputLayout* oldInputLayout = nullptr;
    D3D11_PRIMITIVE_TOPOLOGY oldTopology = D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    ID3D11Buffer* oldVertexConstant = nullptr;
    ID3D11Buffer* oldPixelConstants[2] = {};
    ID3D11ShaderResourceView* oldResources[3] = {};
    ID3D11SamplerState* oldSampler = nullptr;
    ID3D11BlendState* oldBlendState = nullptr;
    FLOAT oldBlendFactor[4] = {};
    UINT oldSampleMask = 0;
    ID3D11DepthStencilState* oldDepthState = nullptr;
    UINT oldStencilReference = 0;
    ID3D11RasterizerState* oldRasterizerState = nullptr;
    ID3D11Predicate* oldPredicate = nullptr;
    BOOL oldPredicateValue = FALSE;
    D3D11_VIEWPORT oldViewports[D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    UINT oldViewportCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    D3D11_RECT oldScissors[D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE] = {};
    UINT oldScissorCount = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;

    context->VSGetShader(&oldVertexShader, oldVertexClasses, &oldVertexClassCount);
    context->PSGetShader(&oldPixelShader, oldPixelClasses, &oldPixelClassCount);
    context->GSGetShader(&oldGeometryShader, oldGeometryClasses, &oldGeometryClassCount);
    context->HSGetShader(&oldHullShader, oldHullClasses, &oldHullClassCount);
    context->DSGetShader(&oldDomainShader, oldDomainClasses, &oldDomainClassCount);
    context->IAGetInputLayout(&oldInputLayout);
    context->IAGetPrimitiveTopology(&oldTopology);
    context->VSGetConstantBuffers(0, 1, &oldVertexConstant);
    context->PSGetConstantBuffers(0, 2, oldPixelConstants);
    context->PSGetShaderResources(0, 3, oldResources);
    context->PSGetSamplers(0, 1, &oldSampler);
    context->OMGetBlendState(&oldBlendState, oldBlendFactor, &oldSampleMask);
    context->OMGetDepthStencilState(&oldDepthState, &oldStencilReference);
    context->RSGetState(&oldRasterizerState);
    context->GetPredication(&oldPredicate, &oldPredicateValue);
    context->RSGetViewports(&oldViewportCount, oldViewports);
    context->RSGetScissorRects(&oldScissorCount, oldScissors);

    const FLOAT blendFactor[4] = {};
    const D3D11_VIEWPORT viewport = {
        0.0f, 0.0f,
        static_cast<FLOAT>(packet->width),
        static_cast<FLOAT>(packet->height),
        0.0f, 1.0f,
    };
    const D3D11_RECT scissor = {
        0, 0,
        static_cast<LONG>(packet->width),
        static_cast<LONG>(packet->height),
    };
    context->SetPredication(nullptr, FALSE);
    context->ClearDepthStencilView(
        g_endminfUberOutputDepthView,
        D3D11_CLEAR_DEPTH | D3D11_CLEAR_STENCIL,
        0.0f,
        0u);
    context->OMSetRenderTargets(
        1u, renderTargets, g_endminfUberOutputDepthView);
    context->IASetInputLayout(nullptr);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_endminfUberVertexShader, nullptr, 0);
    ID3D11PixelShader* selectedPixelShader =
        packet->variant == EndminfUberVariant::Normal
        ? g_endminfUberNormalPixelShader
        : g_endminfUberPixelShader;
    context->PSSetShader(selectedPixelShader, nullptr, 0);
    context->GSSetShader(nullptr, nullptr, 0);
    context->HSSetShader(nullptr, nullptr, 0);
    context->DSSetShader(nullptr, nullptr, 0);
    context->VSSetConstantBuffers(0, 1, &vertexConstant);
    context->PSSetConstantBuffers(0, 2, pixelConstants);
    context->PSSetShaderResources(0, 3, resources);
    context->PSSetSamplers(0, 1, &g_endminfUberSampler);
    context->OMSetBlendState(g_endminfUberBlendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(g_endminfUberDepthState, 0u);
    context->RSSetState(g_endminfUberRasterizerState);
    context->RSSetViewports(1, &viewport);
    context->RSSetScissorRects(1, &scissor);
    context->Draw(3, 0);

    context->OMSetRenderTargets(
        D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT,
        renderTargets,
        renderDepth);

    ID3D11ShaderResourceView* nullResources[3] = {};
    context->PSSetShaderResources(0, 3, nullResources);
    context->VSSetShader(oldVertexShader, oldVertexClasses, oldVertexClassCount);
    context->PSSetShader(oldPixelShader, oldPixelClasses, oldPixelClassCount);
    context->GSSetShader(oldGeometryShader, oldGeometryClasses, oldGeometryClassCount);
    context->HSSetShader(oldHullShader, oldHullClasses, oldHullClassCount);
    context->DSSetShader(oldDomainShader, oldDomainClasses, oldDomainClassCount);
    context->IASetInputLayout(oldInputLayout);
    context->IASetPrimitiveTopology(oldTopology);
    context->VSSetConstantBuffers(0, 1, &oldVertexConstant);
    context->PSSetConstantBuffers(0, 2, oldPixelConstants);
    context->PSSetShaderResources(0, 3, oldResources);
    context->PSSetSamplers(0, 1, &oldSampler);
    context->OMSetBlendState(oldBlendState, oldBlendFactor, oldSampleMask);
    context->OMSetDepthStencilState(oldDepthState, oldStencilReference);
    context->RSSetState(oldRasterizerState);
    context->RSSetViewports(oldViewportCount, oldViewports);
    context->RSSetScissorRects(oldScissorCount, oldScissors);
    context->SetPredication(oldPredicate, oldPredicateValue);

    ReleaseEndminfUberClassInstances(oldDomainClasses, oldDomainClassCount);
    ReleaseEndminfUberClassInstances(oldHullClasses, oldHullClassCount);
    ReleaseEndminfUberClassInstances(oldGeometryClasses, oldGeometryClassCount);
    ReleaseEndminfUberClassInstances(oldPixelClasses, oldPixelClassCount);
    ReleaseEndminfUberClassInstances(oldVertexClasses, oldVertexClassCount);
    ReleaseM14Object(oldPredicate);
    ReleaseM14Object(oldRasterizerState);
    ReleaseM14Object(oldDepthState);
    ReleaseM14Object(oldBlendState);
    ReleaseM14Object(oldSampler);
    for (ID3D11ShaderResourceView*& resource : oldResources)
        ReleaseM14Object(resource);
    for (ID3D11Buffer*& constant : oldPixelConstants)
        ReleaseM14Object(constant);
    ReleaseM14Object(oldVertexConstant);
    ReleaseM14Object(oldInputLayout);
    ReleaseM14Object(oldDomainShader);
    ReleaseM14Object(oldHullShader);
    ReleaseM14Object(oldGeometryShader);
    ReleaseM14Object(oldPixelShader);
    ReleaseM14Object(oldVertexShader);
    for (ID3D11ShaderResourceView*& resource : resources)
        ReleaseM14Object(resource);
    for (ID3D11Buffer*& constant : pixelConstants)
        ReleaseM14Object(constant);
    ReleaseM14Object(vertexConstant);
    ReleaseM14Object(renderDepth);
    ReleaseM14Object(outputTexture);
    ReleaseM14Object(outputResource);
    for (ID3D11RenderTargetView*& target : renderTargets)
        ReleaseM14Object(target);
    context->Release();
    g_endminfUberDrawCount.fetch_add(1, std::memory_order_relaxed);
    g_endminfUberLastResult.store(S_OK, std::memory_order_relaxed);
    g_endminfUberFailureStage.store(0u, std::memory_order_relaxed);
    finishPacket();
}

void UNITY_INTERFACE_API DrawM27ExactRuntime(int eventId)
{
    if (eventId != 0)
        return;
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_m27DrawFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m27DrawLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    HRESULT result = CreateM27DrawResources(device);
    if (FAILED(result))
    {
        ReleaseM27DrawResources();
        g_m27DrawFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m27DrawLastResult.store(result, std::memory_order_relaxed);
        return;
    }
    const std::uint32_t packetIndex =
        g_m27DrawPacketIndex.load(std::memory_order_acquire);
    if (packetIndex >= g_EndfieldM27TemporalFrameCount)
    {
        g_m27DrawFailureStage.store(3001u, std::memory_order_relaxed);
        g_m27DrawFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m27DrawLastResult.store(E_INVALIDARG, std::memory_order_relaxed);
        return;
    }
    const EndfieldM27TemporalFramePayload& packet =
        g_EndfieldM27TemporalFrames[packetIndex];
    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        g_m27DrawFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m27DrawLastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    ID3D11RenderTargetView* renderTargets[5] = {};
    ID3D11DepthStencilView* renderDepth = nullptr;
    context->OMGetRenderTargets(5, renderTargets, &renderDepth);
    bool targetsReady = renderDepth != nullptr;
    for (ID3D11RenderTargetView* target : renderTargets)
        targetsReady = targetsReady && target != nullptr;
    if (!targetsReady)
    {
        g_m27DrawFailureStage.store(3002u, std::memory_order_relaxed);
        ReleaseM14Object(renderDepth);
        for (ID3D11RenderTargetView*& target : renderTargets)
            ReleaseM14Object(target);
        context->Release();
        g_m27DrawFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m27DrawLastResult.store(E_INVALIDARG, std::memory_order_relaxed);
        return;
    }

    ID3D11VertexShader* oldVertexShader = nullptr;
    ID3D11PixelShader* oldPixelShader = nullptr;
    ID3D11InputLayout* oldInputLayout = nullptr;
    ID3D11Buffer* oldVertexBuffers[2] = {};
    ID3D11Buffer* oldIndexBuffer = nullptr;
    ID3D11Buffer* oldVertexCBs[3] = {};
    ID3D11Buffer* oldPixelCBs[5] = {};
    ID3D11ShaderResourceView* oldVertexView = nullptr;
    ID3D11ShaderResourceView* oldPixelViews[6] = {};
    ID3D11SamplerState* oldSamplers[6] = {};
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
    context->VSGetConstantBuffers(0, 3, oldVertexCBs);
    context->PSGetConstantBuffers(0, 5, oldPixelCBs);
    context->VSGetShaderResources(0, 1, &oldVertexView);
    context->PSGetShaderResources(0, 6, oldPixelViews);
    context->PSGetSamplers(0, 6, oldSamplers);
    context->OMGetBlendState(&oldBlendState, oldBlendFactor, &oldSampleMask);
    context->OMGetDepthStencilState(&oldDepthState, &oldStencilReference);
    context->RSGetState(&oldRasterizerState);

    const FLOAT blendFactor[4] = {};
    ID3D11SamplerState* samplers[6] = {
        g_m27DrawSampler, g_m27DrawSampler, g_m27DrawSampler,
        g_m27DrawSampler, g_m27DrawSampler, g_m27DrawSampler,
    };
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_m27DrawVertexShader, nullptr, 0);
    context->PSSetShader(g_m27DrawPixelShader, nullptr, 0);
    context->VSSetShaderResources(0, 1, &g_m27DrawSkinView);
    context->PSSetShaderResources(0, 6, g_m27DrawTextureViews);
    context->PSSetSamplers(0, 6, samplers);
    context->OMSetBlendState(g_m27DrawBlendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(g_m27DrawDepthState, 0);
    context->RSSetState(g_m27DrawRasterizerState);
    for (std::uint32_t drawIndex = 0; drawIndex < packet.drawCount; ++drawIndex)
    {
        const EndfieldM27TemporalDrawPayload& draw = packet.draws[drawIndex];
        const std::size_t layoutIndex = draw.vertexStride == 60u ? 0u : 1u;
        if ((draw.vertexStride != 60u && draw.vertexStride != 68u) ||
            g_m27DrawInputLayouts[layoutIndex] == nullptr)
        {
            g_m27DrawFailureStage.store(
                3100u + drawIndex, std::memory_order_relaxed);
            result = E_INVALIDARG;
            break;
        }
        ID3D11Buffer* vertexBuffers[2] = {
            g_m27DrawVertexBuffers[packetIndex][drawIndex],
            g_m27DrawDefaultVertexBuffer,
        };
        const UINT strides[2] = {draw.vertexStride, 0u};
        const UINT offsets[2] = {};
        context->IASetInputLayout(g_m27DrawInputLayouts[layoutIndex]);
        context->IASetVertexBuffers(0, 2, vertexBuffers, strides, offsets);
        context->IASetIndexBuffer(
            g_m27DrawIndexBuffers[packetIndex][drawIndex],
            DXGI_FORMAT_R16_UINT, 0);
        context->VSSetConstantBuffers(
            0, 3, g_m27DrawVertexConstantBuffers[packetIndex][drawIndex]);
        context->PSSetConstantBuffers(
            0, 5, g_m27DrawPixelConstantBuffers[packetIndex][drawIndex]);
        context->DrawIndexed(draw.indexCount, 0, 0);
    }

    ID3D11ShaderResourceView* nullVertexView = nullptr;
    ID3D11ShaderResourceView* nullPixelViews[6] = {};
    context->VSSetShaderResources(0, 1, &nullVertexView);
    context->PSSetShaderResources(0, 6, nullPixelViews);
    context->IASetInputLayout(oldInputLayout);
    context->IASetVertexBuffers(
        0, 2, oldVertexBuffers, oldVertexStrides, oldVertexOffsets);
    context->IASetIndexBuffer(oldIndexBuffer, oldIndexFormat, oldIndexOffset);
    context->IASetPrimitiveTopology(oldTopology);
    context->VSSetShader(oldVertexShader, nullptr, 0);
    context->PSSetShader(oldPixelShader, nullptr, 0);
    context->VSSetConstantBuffers(0, 3, oldVertexCBs);
    context->PSSetConstantBuffers(0, 5, oldPixelCBs);
    context->VSSetShaderResources(0, 1, &oldVertexView);
    context->PSSetShaderResources(0, 6, oldPixelViews);
    context->PSSetSamplers(0, 6, oldSamplers);
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
    for (ID3D11RenderTargetView*& target : renderTargets)
        ReleaseM14Object(target);
    context->Release();
    if (FAILED(result))
    {
        g_m27DrawFailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m27DrawLastResult.store(result, std::memory_order_relaxed);
        return;
    }
    g_m27DrawCount.fetch_add(packet.drawCount, std::memory_order_relaxed);
    g_m27DrawLastResult.store(S_OK, std::memory_order_relaxed);
}
} // namespace

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
UnityPluginLoad(IUnityInterfaces* unityInterfaces)
{
    ReleaseRuntimeShaders();
    ReleaseEndminfUberRuntimeResources();
    ReleaseM27DrawResources();
    ReleaseM29RuntimeResources();
    ReleaseM13RuntimeResources();
    ReleaseOpeningStripResources();
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
    ReleaseEndminfUberRuntimeResources();
    ReleaseM27DrawResources();
    ReleaseM29RuntimeResources();
    ReleaseM13RuntimeResources();
    ReleaseOpeningStripResources();
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

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM18PeakRenderEventFunc()
{
    return DrawM18PeakExactRuntime;
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM28PeakRenderEventFunc()
{
    return DrawM28PeakExactRuntime;
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM21PeakRenderEventFunc()
{
    return DrawM21PeakExactRuntime;
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM20PeakRenderEventFunc()
{
    return DrawM20PeakExactRuntime;
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM31PeakRenderEventFunc()
{
    return DrawM31PeakExactRuntime;
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetVFXBaseV2PeakCohortRenderEventFunc()
{
    return DrawVFXBaseV2PeakCohortRuntime;
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM30RenderEventFunc()
{
    return DrawM30ExactRuntime;
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM29RenderEventFunc()
{
    return DrawM29ExactRuntime;
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM13RenderEventFunc()
{
    return DrawM13ExactRuntime;
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetOpeningStripRenderEventFunc()
{
    return DrawOpeningStripExactRuntime;
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27RenderEventFunc()
{
    return DrawM27ExactRuntime;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetEndminfUberPayloadReady()
{
    return g_EndfieldUberCapturePayloadAvailable ? 1u : 0u;
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetEndminfUberRenderEventFunc()
{
    return DrawEndminfUberExactRuntime;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetEndminfUberTextureResources(
    void* source,
    void* bloom,
    void* lut)
{
    void* pointers[3] = {source, bloom, lut};
    ID3D11Texture2D* textures[3] = {};
    HRESULT result = S_OK;
    for (std::size_t index = 0; index < 3; ++index)
    {
        if (pointers[index] == nullptr)
        {
            result = E_POINTER;
            break;
        }
        result = reinterpret_cast<IUnknown*>(pointers[index])->QueryInterface(
            __uuidof(ID3D11Texture2D),
            reinterpret_cast<void**>(&textures[index]));
        if (FAILED(result) || textures[index] == nullptr)
            break;
    }

    if (SUCCEEDED(result))
    {
        D3D11_TEXTURE2D_DESC sourceDescription = {};
        textures[0]->GetDesc(&sourceDescription);
        if (!ValidateEndminfUberTextureSet(
                textures, sourceDescription.Width, sourceDescription.Height))
        {
            result = E_INVALIDARG;
        }
    }
    if (SUCCEEDED(result))
    {
        ID3D11Device* devices[3] = {};
        for (std::size_t index = 0; index < 3; ++index)
            textures[index]->GetDevice(&devices[index]);
        const bool sameDevice = devices[0] != nullptr &&
            devices[0] == devices[1] && devices[0] == devices[2];
        for (ID3D11Device*& device : devices)
            ReleaseM14Object(device);
        if (!sameDevice)
            result = E_INVALIDARG;
    }

    {
        std::lock_guard<std::mutex> lock(g_endminfUberMutex);
        for (ID3D11Texture2D*& old : g_endminfUberConfiguredTextures)
            ReleaseM14Object(old);
        if (SUCCEEDED(result))
        {
            for (std::size_t index = 0; index < 3; ++index)
            {
                g_endminfUberConfiguredTextures[index] = textures[index];
                textures[index] = nullptr;
            }
        }
    }
    for (ID3D11Texture2D*& texture : textures)
        ReleaseM14Object(texture);
    if (FAILED(result))
    {
        RecordEndminfUberFailure(result, 301u);
        return 0u;
    }
    g_endminfUberLastResult.store(S_OK, std::memory_order_relaxed);
    g_endminfUberFailureStage.store(0u, std::memory_order_relaxed);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcQueueEndminfUberPacketVariant(
    std::uint32_t variant,
    float screenWidth,
    float screenHeight,
    float exposure,
    float centerX,
    float centerY,
    float radialIntensity,
    float power)
{
    if (!g_EndfieldUberCapturePayloadAvailable)
    {
        RecordEndminfUberFailure(
            HRESULT_FROM_WIN32(ERROR_FILE_NOT_FOUND), 401u);
        return 0u;
    }
    const bool validVariant =
        variant <= static_cast<std::uint32_t>(EndminfUberVariant::Peak);
    const bool finite = std::isfinite(screenWidth) &&
        std::isfinite(screenHeight) && std::isfinite(exposure) &&
        std::isfinite(centerX) && std::isfinite(centerY) &&
        std::isfinite(radialIntensity) && std::isfinite(power);
    const bool validDimensions = screenWidth >= 1.0f &&
        screenHeight >= 1.0f && screenWidth <= 16384.0f &&
        screenHeight <= 16384.0f &&
        std::floor(screenWidth) == screenWidth &&
        std::floor(screenHeight) == screenHeight;
    const bool validParams = centerX >= 0.0f && centerX <= 1.0f &&
        centerY >= 0.0f && centerY <= 1.0f &&
        radialIntensity >= 0.0f && power > 0.0f;
    if (!validVariant || !finite || !validDimensions || !validParams)
    {
        RecordEndminfUberFailure(E_INVALIDARG, 402u);
        return 0u;
    }

    const UINT width = static_cast<UINT>(screenWidth);
    const UINT height = static_cast<UINT>(screenHeight);
    std::lock_guard<std::mutex> lock(g_endminfUberMutex);
    if (!ValidateEndminfUberTextureSet(
            g_endminfUberConfiguredTextures, width, height))
    {
        RecordEndminfUberFailure(E_INVALIDARG, 403u);
        return 0u;
    }
    EndminfUberPacket* packet = nullptr;
    for (EndminfUberPacket& candidate : g_endminfUberPackets)
    {
        if (candidate.state.load(std::memory_order_acquire) ==
            EndminfUberPacketState::Empty)
        {
            packet = &candidate;
            break;
        }
    }
    if (packet == nullptr)
    {
        RecordEndminfUberFailure(
            HRESULT_FROM_WIN32(ERROR_NOT_ENOUGH_MEMORY), 404u);
        return 0u;
    }
    const std::uint32_t eventId = AllocateEndminfUberEventId();
    if (eventId == 0u)
    {
        RecordEndminfUberFailure(E_FAIL, 405u);
        return 0u;
    }

    std::memcpy(packet->vsB0, g_EndfieldUberVsB0, sizeof(packet->vsB0));
    std::memcpy(packet->psB0, g_EndfieldUberPsB0, sizeof(packet->psB0));
    std::memcpy(packet->psB1, g_EndfieldUberPsB1, sizeof(packet->psB1));
    // ShaderVariablesGlobal._ScreenSize = (width, height, rcpWidth, rcpHeight).
    PatchEndminfUberFloat(packet->psB0, sizeof(packet->psB0), 0u, screenWidth);
    PatchEndminfUberFloat(packet->psB0, sizeof(packet->psB0), 1u, screenHeight);
    PatchEndminfUberFloat(
        packet->psB0, sizeof(packet->psB0), 2u, 1.0f / screenWidth);
    PatchEndminfUberFloat(
        packet->psB0, sizeof(packet->psB0), 3u, 1.0f / screenHeight);
    PatchEndminfUberFloat(packet->psB0, sizeof(packet->psB0), 27u * 4u, exposure);
    // ShaderVariablesGlobal c27.z is the target aspect ratio. Both captured
    // Uber variants read it, so it must follow the live output dimensions.
    PatchEndminfUberFloat(
        packet->psB0, sizeof(packet->psB0), 27u * 4u + 2u,
        screenWidth / screenHeight);
    PatchEndminfUberFloat(packet->psB1, sizeof(packet->psB1), 0u, centerX);
    PatchEndminfUberFloat(packet->psB1, sizeof(packet->psB1), 1u, centerY);
    PatchEndminfUberFloat(
        packet->psB1, sizeof(packet->psB1), 2u, radialIntensity);
    PatchEndminfUberFloat(packet->psB1, sizeof(packet->psB1), 3u, power);
    // The active RADIAL_BLUR + VIGNETTE variant reads the dynamic c0 lanes.
    // Preserve c25 and every vignette/bloom/LUT lane exactly as captured.
    for (std::size_t index = 0; index < 3; ++index)
    {
        packet->textures[index] = g_endminfUberConfiguredTextures[index];
        packet->textures[index]->AddRef();
    }
    packet->width = width;
    packet->height = height;
    packet->variant = static_cast<EndminfUberVariant>(variant);
    packet->eventId.store(eventId, std::memory_order_relaxed);
    packet->state.store(EndminfUberPacketState::Ready, std::memory_order_release);
    g_endminfUberLastResult.store(S_OK, std::memory_order_relaxed);
    g_endminfUberFailureStage.store(0u, std::memory_order_relaxed);
    return eventId;
}

// ABI-compatible peak-only entry point retained for older managed clients.
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcQueueEndminfUberPacket(
    float screenWidth,
    float screenHeight,
    float exposure,
    float centerX,
    float centerY,
    float radialIntensity,
    float power)
{
    return EndfieldOriginalDxbcQueueEndminfUberPacketVariant(
        static_cast<std::uint32_t>(EndminfUberVariant::Peak),
        screenWidth,
        screenHeight,
        exposure,
        centerX,
        centerY,
        radialIntensity,
        power);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcInspectEndminfUberQueuedPacket(
    std::uint32_t eventId,
    std::uint32_t* variant,
    float* aspect)
{
    if (eventId == 0u || variant == nullptr || aspect == nullptr)
        return 0u;
    std::lock_guard<std::mutex> lock(g_endminfUberMutex);
    for (const EndminfUberPacket& packet : g_endminfUberPackets)
    {
        if (packet.state.load(std::memory_order_acquire) !=
                EndminfUberPacketState::Ready ||
            packet.eventId.load(std::memory_order_relaxed) != eventId)
        {
            continue;
        }
        *variant = static_cast<std::uint32_t>(packet.variant);
        std::memcpy(
            aspect,
            packet.psB0 + (27u * 4u + 2u) * sizeof(float),
            sizeof(float));
        return 1u;
    }
    return 0u;
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetEndminfUberRuntimeState()
{
    std::lock_guard<std::mutex> lock(g_endminfUberMutex);
    for (ID3D11Texture2D*& texture : g_endminfUberConfiguredTextures)
        ReleaseM14Object(texture);
    for (EndminfUberPacket& packet : g_endminfUberPackets)
    {
        EndminfUberPacketState expected = EndminfUberPacketState::Ready;
        if (packet.state.compare_exchange_strong(
                expected,
                EndminfUberPacketState::Consuming,
                std::memory_order_acq_rel))
        {
            ReleaseEndminfUberPacketTextures(packet);
            packet.eventId.store(0u, std::memory_order_relaxed);
            packet.state.store(
                EndminfUberPacketState::Empty, std::memory_order_release);
        }
    }
    g_endminfUberNextEventId = 1;
    g_endminfUberDrawCount.store(0u, std::memory_order_relaxed);
    g_endminfUberFailureCount.store(0u, std::memory_order_relaxed);
    g_endminfUberLastResult.store(S_OK, std::memory_order_relaxed);
    g_endminfUberFailureStage.store(0u, std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetEndminfUberDrawCount()
{
    return g_endminfUberDrawCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetEndminfUberFailureCount()
{
    return g_endminfUberFailureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetEndminfUberLastResult()
{
    return static_cast<std::int32_t>(
        g_endminfUberLastResult.load(std::memory_order_relaxed));
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetEndminfUberFailureStage()
{
    return g_endminfUberFailureStage.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM27TextureResources(
    void* texture0,
    void* texture1,
    void* texture2,
    void* texture3,
    void* texture4,
    void* texture5)
{
    // Retained for ABI compatibility with older managed players. Temporal M27
    // now owns hash-pinned captured textures inside the native payload.
    (void)texture0; (void)texture1; (void)texture2;
    (void)texture3; (void)texture4; (void)texture5;
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM27PacketIndex(std::uint32_t packetIndex)
{
    if (packetIndex >= g_EndfieldM27TemporalFrameCount)
        return 0u;
    g_m27DrawPacketIndex.store(packetIndex, std::memory_order_release);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27PacketCount()
{
    return g_EndfieldM27TemporalFrameCount;
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetM27RuntimeState()
{
    g_m27DrawPacketIndex.store(0, std::memory_order_release);
    g_m27DrawCount.store(0, std::memory_order_relaxed);
    g_m27DrawFailureCount.store(0, std::memory_order_relaxed);
    g_m27DrawLastResult.store(S_OK, std::memory_order_relaxed);
    g_m27DrawFailureStage.store(0u, std::memory_order_relaxed);
    ReleaseM27DrawResources();
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27DrawCount()
{
    return g_m27DrawCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27DrawFailureCount()
{
    return g_m27DrawFailureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27DrawLastResult()
{
    return static_cast<std::int32_t>(
        g_m27DrawLastResult.load(std::memory_order_relaxed));
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27DrawFailureStage()
{
    return g_m27DrawFailureStage.load(std::memory_order_relaxed);
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetM13RuntimeState()
{
    g_m13OutputDimensions.store(0, std::memory_order_release);
    g_m13ScreenSizePatched.store(0, std::memory_order_release);
    g_m13PacketIndex.store(0, std::memory_order_relaxed);
    g_m13DrawCount.store(0, std::memory_order_relaxed);
    g_m13FailureCount.store(0, std::memory_order_relaxed);
    g_m13LastResult.store(S_OK, std::memory_order_relaxed);
    ReleaseM13RuntimeResources();
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM13OutputDimensions(
    std::uint32_t width,
    std::uint32_t height)
{
    if (width == 0 || height == 0 ||
        width > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION ||
        height > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION)
        return 0u;
    for (const EndfieldM13PacketPayload& packet : g_EndfieldM13Packets)
    {
        if (!IsCapturedM20ScreenConstants(packet.vs[2], packet.vsBytes[2]) ||
            !IsCapturedM20ScreenConstants(packet.ps[1], packet.psBytes[1]))
            return 0u;
    }
    const std::uint64_t packed = PackOpeningStripDimensions(width, height);
    const std::uint64_t previous = g_m13OutputDimensions.exchange(
        packed, std::memory_order_acq_rel);
    if (previous != packed)
        g_m13ScreenSizePatched.store(0u, std::memory_order_release);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM13ScreenSizePatchStatus()
{
    return g_m13ScreenSizePatched.load(std::memory_order_acquire);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM13PacketCount()
{
    return g_EndfieldM13PacketCount;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM13PacketIndex(std::uint32_t packetIndex)
{
    if (packetIndex >= g_EndfieldM13PacketCount)
        return 0u;
    g_m13PacketIndex.store(packetIndex, std::memory_order_release);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM13DrawCount()
{
    return g_m13DrawCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM13FailureCount()
{
    return g_m13FailureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM13LastResult()
{
    return static_cast<std::int32_t>(
        g_m13LastResult.load(std::memory_order_relaxed));
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetOpeningStripTextureResources(
    void* sceneColorTexture)
{
    g_openingStripSceneColor.store(
        reinterpret_cast<std::uintptr_t>(sceneColorTexture),
        std::memory_order_release);
    return sceneColorTexture != nullptr ? 1u : 0u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetOpeningStripOutputDimensions(
    std::uint32_t width,
    std::uint32_t height)
{
    if (width == 0 || height == 0 ||
        width > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION ||
        height > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION)
        return 0u;
    for (const EndfieldOpeningStripPacket& packet : g_EndfieldOpeningStripPackets)
    {
        if (!IsCapturedOpeningStripScreenSize(packet.vs[2], packet.vsBytes[2]) ||
            !IsCapturedOpeningStripScreenSize(packet.ps[1], packet.psBytes[1]))
            return 0u;
    }
    const std::uint64_t packed = PackOpeningStripDimensions(width, height);
    const std::uint64_t previous = g_openingStripOutputDimensions.exchange(
        packed, std::memory_order_acq_rel);
    if (previous != packed)
        g_openingStripScreenSizePatched.store(0u, std::memory_order_release);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetOpeningStripScreenSizePatchStatus()
{
    return g_openingStripScreenSizePatched.load(std::memory_order_acquire);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetOpeningStripPacketIndex(std::uint32_t packetIndex)
{
    if (packetIndex >= g_EndfieldOpeningStripPacketCount) return 0u;
    g_openingStripPacketIndex.store(packetIndex, std::memory_order_release);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetOpeningStripPacketCount()
{
    return g_EndfieldOpeningStripPacketCount;
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetOpeningStripRuntimeState()
{
    g_openingStripPacketIndex.store(0, std::memory_order_relaxed);
    g_openingStripDrawCount.store(0, std::memory_order_relaxed);
    g_openingStripFailureCount.store(0, std::memory_order_relaxed);
    g_openingStripLastResult.store(S_OK, std::memory_order_relaxed);
    g_openingStripSceneColor.store(0, std::memory_order_relaxed);
    g_openingStripOutputDimensions.store(0, std::memory_order_relaxed);
    g_openingStripScreenSizePatched.store(0, std::memory_order_relaxed);
    ReleaseOpeningStripResources();
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetOpeningStripDrawCount()
{
    return g_openingStripDrawCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetOpeningStripFailureCount()
{
    return g_openingStripFailureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetOpeningStripLastResult()
{
    return static_cast<std::int32_t>(
        g_openingStripLastResult.load(std::memory_order_relaxed));
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

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM14PacketIndex(std::uint32_t packetIndex)
{
    if (packetIndex >= g_EndfieldM14PacketCount)
        return 0u;
    g_m14PacketIndex.store(packetIndex, std::memory_order_release);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM14PacketCount()
{
    return g_EndfieldM14PacketCount;
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetM14RuntimeState()
{
    g_m14DepthTexture.store(0, std::memory_order_release);
    g_m14MainTexture.store(0, std::memory_order_release);
    g_m14OutputDimensions.store(0, std::memory_order_release);
    g_m14ScreenSizePatched.store(0, std::memory_order_release);
    g_m14PacketIndex.store(0, std::memory_order_release);
    g_m14DrawCount.store(0, std::memory_order_relaxed);
    g_m14FailureCount.store(0, std::memory_order_relaxed);
    g_m14LastResult.store(S_OK, std::memory_order_relaxed);
    ReleaseM14RuntimeResources();
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM14OutputDimensions(
    std::uint32_t width,
    std::uint32_t height)
{
    if (width == 0 || height == 0 ||
        width > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION ||
        height > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION)
        return 0u;
    for (const EndfieldM14PacketPayload& packet : g_EndfieldM14Packets)
    {
        if (!IsCapturedM20ScreenConstants(packet.vs[2], packet.vsBytes[2]) ||
            !IsCapturedM20ScreenConstants(packet.ps[1], packet.psBytes[1]))
            return 0u;
    }
    const std::uint64_t packed = PackOpeningStripDimensions(width, height);
    const std::uint64_t previous = g_m14OutputDimensions.exchange(
        packed, std::memory_order_acq_rel);
    if (previous != packed)
        g_m14ScreenSizePatched.store(0u, std::memory_order_release);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM14ScreenSizePatchStatus()
{
    return g_m14ScreenSizePatched.load(std::memory_order_acquire);
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
EndfieldOriginalDxbcSetVFXBaseV2PeakCohortDepthResource(void* sceneDepth)
{
    g_vfxPeakDepthTexture.store(
        reinterpret_cast<std::uintptr_t>(sceneDepth),
        std::memory_order_release);
    return sceneDepth != nullptr ? 1u : 0u;
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetVFXBaseV2PeakCohortRuntimeState()
{
    g_vfxPeakDepthTexture.store(0, std::memory_order_release);
    g_vfxPeakDrawCount.store(0, std::memory_order_relaxed);
    g_vfxPeakFailureCount.store(0, std::memory_order_relaxed);
    g_vfxPeakLastResult.store(S_OK, std::memory_order_relaxed);
    ReleaseM14RuntimeResources();
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetVFXBaseV2PeakCohortDrawCount()
{
    return g_vfxPeakDrawCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetVFXBaseV2PeakCohortFailureCount()
{
    return g_vfxPeakFailureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetVFXBaseV2PeakCohortLastResult()
{
    return static_cast<std::int32_t>(
        g_vfxPeakLastResult.load(std::memory_order_relaxed));
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM18PeakTextureResources(
    void* t0, void* t1, void* t2, void* t3, void* t4)
{
    void* values[5] = {t0, t1, t2, t3, t4};
    for (std::size_t slot = 0; slot < 5; ++slot)
    {
        if (values[slot] == nullptr)
            return 0u;
    }
    for (std::size_t slot = 0; slot < 5; ++slot)
    {
        g_m18PeakTextures[slot].store(
            reinterpret_cast<std::uintptr_t>(values[slot]),
            std::memory_order_release);
    }
    return 1u;
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetM18PeakRuntimeState()
{
    for (std::atomic<std::uintptr_t>& texture : g_m18PeakTextures)
        texture.store(0, std::memory_order_release);
    g_m18PeakOutputDimensions.store(0, std::memory_order_release);
    g_m18PeakScreenSizePatched.store(0, std::memory_order_release);
    g_m18PeakResourceWidth = 0;
    g_m18PeakResourceHeight = 0;
    g_m18PeakDrawCount.store(0, std::memory_order_relaxed);
    g_m18PeakFailureCount.store(0, std::memory_order_relaxed);
    g_m18PeakLastResult.store(S_OK, std::memory_order_relaxed);
    ReleaseM14RuntimeResources();
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM18PeakOutputDimensions(
    std::uint32_t width, std::uint32_t height)
{
    if (width == 0 || height == 0 ||
        width > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION ||
        height > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION ||
        !IsCapturedM20ScreenConstants(
            g_EndfieldM18PeakVSCB2, g_EndfieldM18PeakVSCB2Size) ||
        !IsCapturedM20ScreenConstants(
            g_EndfieldM18PeakPSCB1, g_EndfieldM18PeakPSCB1Size))
        return 0u;
    const std::uint64_t packed = PackOpeningStripDimensions(width, height);
    const std::uint64_t previous = g_m18PeakOutputDimensions.exchange(
        packed, std::memory_order_acq_rel);
    if (previous != packed)
        g_m18PeakScreenSizePatched.store(0u, std::memory_order_release);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM18PeakScreenSizePatchStatus()
{
    return g_m18PeakScreenSizePatched.load(std::memory_order_acquire);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM18PeakDrawCount()
{
    return g_m18PeakDrawCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM18PeakFailureCount()
{
    return g_m18PeakFailureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM18PeakLastResult()
{
    return static_cast<std::int32_t>(
        g_m18PeakLastResult.load(std::memory_order_relaxed));
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM28PeakTextureResources(void* t0, void* t1, void* t2)
{
    void* values[3] = {t0, t1, t2};
    for (void* value : values)
    {
        if (value == nullptr)
            return 0u;
    }
    for (std::size_t slot = 0; slot < 3; ++slot)
    {
        g_m28PeakTextures[slot].store(
            reinterpret_cast<std::uintptr_t>(values[slot]),
            std::memory_order_release);
    }
    return 1u;
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetM28PeakRuntimeState()
{
    for (std::atomic<std::uintptr_t>& texture : g_m28PeakTextures)
        texture.store(0, std::memory_order_release);
    g_m28PeakOutputDimensions.store(0, std::memory_order_release);
    g_m28PeakScreenSizePatched.store(0, std::memory_order_release);
    g_m28PeakResourceWidth = 0;
    g_m28PeakResourceHeight = 0;
    g_m28PeakDrawCount.store(0, std::memory_order_relaxed);
    g_m28PeakFailureCount.store(0, std::memory_order_relaxed);
    g_m28PeakLastResult.store(S_OK, std::memory_order_relaxed);
    ReleaseM14RuntimeResources();
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM28PeakOutputDimensions(
    std::uint32_t width, std::uint32_t height)
{
    if (width == 0 || height == 0 ||
        width > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION ||
        height > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION ||
        !IsCapturedM20ScreenConstants(
            g_EndfieldM28PeakVSCB2, g_EndfieldM28PeakVSCB2Size) ||
        !IsCapturedM20ScreenConstants(
            g_EndfieldM28PeakPSCB1, g_EndfieldM28PeakPSCB1Size))
        return 0u;
    const std::uint64_t packed = PackOpeningStripDimensions(width, height);
    const std::uint64_t previous = g_m28PeakOutputDimensions.exchange(
        packed, std::memory_order_acq_rel);
    if (previous != packed)
        g_m28PeakScreenSizePatched.store(0u, std::memory_order_release);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM28PeakScreenSizePatchStatus()
{
    return g_m28PeakScreenSizePatched.load(std::memory_order_acquire);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM28PeakDrawCount()
{
    return g_m28PeakDrawCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM28PeakFailureCount()
{
    return g_m28PeakFailureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM28PeakLastResult()
{
    return static_cast<std::int32_t>(
        g_m28PeakLastResult.load(std::memory_order_relaxed));
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetM21PeakRuntimeState()
{
    g_m21PeakOutputDimensions.store(0, std::memory_order_release);
    g_m21PeakScreenSizePatched.store(0, std::memory_order_release);
    g_m21PeakDrawCount.store(0, std::memory_order_relaxed);
    g_m21PeakFailureCount.store(0, std::memory_order_relaxed);
    g_m21PeakLastResult.store(S_OK, std::memory_order_relaxed);
    ReleaseM14RuntimeResources();
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM21PeakOutputDimensions(
    std::uint32_t width,
    std::uint32_t height)
{
    if (width == 0 || height == 0 ||
        width > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION ||
        height > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION ||
        !IsCapturedM20ScreenConstants(
            g_EndfieldM21PeakVSCB2, g_EndfieldM21PeakVSCB2Size) ||
        !IsCapturedM20ScreenConstants(
            g_EndfieldM21PeakPSCB1, g_EndfieldM21PeakPSCB1Size))
        return 0u;
    const std::uint64_t packed = PackOpeningStripDimensions(width, height);
    const std::uint64_t previous = g_m21PeakOutputDimensions.exchange(
        packed, std::memory_order_acq_rel);
    if (previous != packed)
        g_m21PeakScreenSizePatched.store(0u, std::memory_order_release);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM21PeakScreenSizePatchStatus()
{
    return g_m21PeakScreenSizePatched.load(std::memory_order_acquire);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM21PeakDrawCount()
{
    return g_m21PeakDrawCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM21PeakFailureCount()
{
    return g_m21PeakFailureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM21PeakLastResult()
{
    return static_cast<std::int32_t>(
        g_m21PeakLastResult.load(std::memory_order_relaxed));
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM20PeakDepthResource(void* sceneDepth)
{
    g_m20PeakDepthTexture.store(
        reinterpret_cast<std::uintptr_t>(sceneDepth), std::memory_order_release);
    return sceneDepth != nullptr ? 1u : 0u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM20PeakOutputDimensions(
    std::uint32_t width,
    std::uint32_t height)
{
    if (width == 0 || height == 0 ||
        width > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION ||
        height > D3D11_REQ_TEXTURE2D_U_OR_V_DIMENSION ||
        !IsCapturedM20ScreenConstants(
            g_EndfieldM20PeakVSCB2, g_EndfieldM20PeakVSCB2Size) ||
        !IsCapturedM20ScreenConstants(
            g_EndfieldM20PeakPSCB1, g_EndfieldM20PeakPSCB1Size))
        return 0u;
    const std::uint64_t packed = PackOpeningStripDimensions(width, height);
    const std::uint64_t previous = g_m20PeakOutputDimensions.exchange(
        packed, std::memory_order_acq_rel);
    if (previous != packed)
        g_m20PeakScreenSizePatched.store(0u, std::memory_order_release);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM20PeakScreenSizePatchStatus()
{
    return g_m20PeakScreenSizePatched.load(std::memory_order_acquire);
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetM20PeakRuntimeState()
{
    g_m20PeakDepthTexture.store(0, std::memory_order_release);
    g_m20PeakOutputDimensions.store(0, std::memory_order_release);
    g_m20PeakScreenSizePatched.store(0, std::memory_order_release);
    g_m20PeakDrawCount.store(0, std::memory_order_relaxed);
    g_m20PeakFailureCount.store(0, std::memory_order_relaxed);
    g_m20PeakLastResult.store(S_OK, std::memory_order_relaxed);
    ReleaseM14RuntimeResources();
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM20PeakDrawCount()
{
    return g_m20PeakDrawCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM20PeakFailureCount()
{
    return g_m20PeakFailureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM20PeakLastResult()
{
    return static_cast<std::int32_t>(
        g_m20PeakLastResult.load(std::memory_order_relaxed));
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM31PeakDepthResource(void* sceneDepth)
{
    g_m31PeakDepthTexture.store(
        reinterpret_cast<std::uintptr_t>(sceneDepth),
        std::memory_order_release);
    return sceneDepth != nullptr ? 1u : 0u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM31PeakTemporalPacketIndex(std::uint32_t packetIndex)
{
    g_m31PeakTemporalPacketIndex.store(
        (std::numeric_limits<std::uint32_t>::max)(), std::memory_order_release);
    if (packetIndex >= g_EndfieldM31PeakTemporalPacketCount)
        return 0u;
    const EndfieldM31PeakTemporalPacket& packet =
        g_EndfieldM31PeakTemporalPackets[packetIndex];
    const bool supportedSchedule =
        (packet.scheduleProfile ==
                g_EndfieldM31PeakScheduleQueue3000Interval2 &&
            packet.drawCount == 2u) ||
        (packet.scheduleProfile ==
                g_EndfieldM31PeakScheduleQueue3000ThenPostM18_3 &&
            packet.drawCount == 3u);
    if (!packet.chronologyValidated || !supportedSchedule ||
        packet.firstDrawPayload + packet.drawCount >
            g_EndfieldM31PeakDrawPayloadCount)
        return 0u;
    g_m31PeakTemporalPacketIndex.store(packetIndex, std::memory_order_release);
    return 1u;
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetM31PeakRuntimeState()
{
    g_m31PeakDepthTexture.store(0, std::memory_order_release);
    g_m31PeakTemporalPacketIndex.store(
        (std::numeric_limits<std::uint32_t>::max)(), std::memory_order_release);
    g_m31PeakDrawCount.store(0, std::memory_order_relaxed);
    g_m31PeakFailureCount.store(0, std::memory_order_relaxed);
    g_m31PeakLastResult.store(S_OK, std::memory_order_relaxed);
    ReleaseM14RuntimeResources();
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM31PeakDrawCount()
{
    return g_m31PeakDrawCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM31PeakFailureCount()
{
    return g_m31PeakFailureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM31PeakLastResult()
{
    return static_cast<std::int32_t>(
        g_m31PeakLastResult.load(std::memory_order_relaxed));
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM30DepthResource(void* sceneDepth)
{
    g_m30DepthTexture.store(
        reinterpret_cast<std::uintptr_t>(sceneDepth), std::memory_order_release);
    return sceneDepth != nullptr ? 1u : 0u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM30PacketIndex(std::uint32_t packetIndex)
{
    if (packetIndex >= g_EndfieldM30PacketCount)
        return 0u;
    g_m30PacketIndex.store(packetIndex, std::memory_order_release);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM30PacketCount()
{
    return g_EndfieldM30PacketCount;
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetM30RuntimeState()
{
    g_m30DepthTexture.store(0, std::memory_order_release);
    g_m30PacketIndex.store(0, std::memory_order_release);
    g_m30DrawCount.store(0, std::memory_order_relaxed);
    g_m30FailureCount.store(0, std::memory_order_relaxed);
    g_m30LastResult.store(S_OK, std::memory_order_relaxed);
    ReleaseM14RuntimeResources();
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM30DrawCount()
{
    return g_m30DrawCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM30FailureCount()
{
    return g_m30FailureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM30LastResult()
{
    return static_cast<std::int32_t>(
        g_m30LastResult.load(std::memory_order_relaxed));
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM29DepthResource(void* sceneDepth)
{
    g_m29DepthTexture.store(
        reinterpret_cast<std::uintptr_t>(sceneDepth), std::memory_order_release);
    return sceneDepth != nullptr ? 1u : 0u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM29PacketIndex(std::uint32_t packetIndex)
{
    if (packetIndex >= g_EndfieldM29PacketCount)
        return 0u;
    g_m29PacketIndex.store(packetIndex, std::memory_order_release);
    return 1u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM29PacketCount()
{
    return g_EndfieldM29PacketCount;
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetM29RuntimeState()
{
    g_m29DepthTexture.store(0, std::memory_order_release);
    g_m29PacketIndex.store(0, std::memory_order_release);
    g_m29DrawCount.store(0, std::memory_order_relaxed);
    g_m29FailureCount.store(0, std::memory_order_relaxed);
    g_m29LastResult.store(S_OK, std::memory_order_relaxed);
    ReleaseM29RuntimeResources();
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM29DrawCount()
{
    return g_m29DrawCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM29FailureCount()
{
    return g_m29FailureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM29LastResult()
{
    return static_cast<std::int32_t>(
        g_m29LastResult.load(std::memory_order_relaxed));
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
