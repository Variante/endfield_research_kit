#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <bcrypt.h>
#include <d3d11.h>

#include <cstdio>
#include <cstring>

#include "M27SubstitutionRegistry.h"

namespace
{
bool Sha256(const unsigned char* data, std::size_t size, unsigned char digest[32])
{
    return BCRYPT_SUCCESS(BCryptHash(
        BCRYPT_SHA256_ALG_HANDLE,
        nullptr,
        0,
        const_cast<PUCHAR>(data),
        static_cast<ULONG>(size),
        digest,
        32));
}
}

int main()
{
    unsigned char digest[32] = {};
    bool hashesValid =
        Sha256(
            g_EndfieldM27VertexDxbc,
            g_EndfieldM27VertexDxbcSize,
            digest) &&
        std::memcmp(digest, g_EndfieldM27VertexDxbcSha256, 32) == 0 &&
        Sha256(
            g_EndfieldM27PixelDxbc,
            g_EndfieldM27PixelDxbcSize,
            digest) &&
        std::memcmp(digest, g_EndfieldM27PixelDxbcSha256, 32) == 0 &&
        Sha256(
            g_EndfieldM14VertexDxbc,
            g_EndfieldM14VertexDxbcSize,
            digest) &&
        std::memcmp(digest, g_EndfieldM14VertexDxbcSha256, 32) == 0 &&
        Sha256(
            g_EndfieldM14PixelDxbc,
            g_EndfieldM14PixelDxbcSize,
            digest) &&
        std::memcmp(digest, g_EndfieldM14PixelDxbcSha256, 32) == 0;

    unsigned char unknownShellHash[32] = {};
    unknownShellHash[0] = 1;
    const bool dispatchValid =
        EndfieldM27Substitution::Ready() &&
        EndfieldM27Substitution::Resolve(
            EndfieldM27Substitution::Stage::Vertex,
            unknownShellHash) == nullptr &&
        EndfieldM27Substitution::Resolve(
            EndfieldM27Substitution::Stage::Pixel,
            unknownShellHash) == nullptr &&
        EndfieldM27Substitution::Resolve(
            EndfieldM27Substitution::Stage::Vertex,
            EndfieldM27Substitution::kEntries[0].shellSha256) ==
                &EndfieldM27Substitution::kEntries[0] &&
        EndfieldM27Substitution::Resolve(
            EndfieldM27Substitution::Stage::Pixel,
            EndfieldM27Substitution::kEntries[1].shellSha256) ==
                &EndfieldM27Substitution::kEntries[1] &&
        EndfieldM27Substitution::Resolve(
            EndfieldM27Substitution::Stage::Vertex,
            EndfieldM27Substitution::kEntries[1].shellSha256) == nullptr &&
        EndfieldM27Substitution::Resolve(
            EndfieldM27Substitution::Stage::Pixel,
            EndfieldM27Substitution::kEntries[0].shellSha256) == nullptr;
    const bool m14DispatchValid =
        EndfieldM27Substitution::Resolve(
            EndfieldM27Substitution::Stage::Vertex,
            EndfieldM27Substitution::kEntries[2].shellSha256) ==
                &EndfieldM27Substitution::kEntries[2] &&
        EndfieldM27Substitution::Resolve(
            EndfieldM27Substitution::Stage::Pixel,
            EndfieldM27Substitution::kEntries[3].shellSha256) ==
                &EndfieldM27Substitution::kEntries[3] &&
        EndfieldM27Substitution::Resolve(
            EndfieldM27Substitution::Stage::Pixel,
            EndfieldM27Substitution::kEntries[2].shellSha256) == nullptr &&
        EndfieldM27Substitution::Resolve(
            EndfieldM27Substitution::Stage::Vertex,
            EndfieldM27Substitution::kEntries[3].shellSha256) == nullptr;

    ID3D11Device* device = nullptr;
    ID3D11DeviceContext* context = nullptr;
    const D3D_FEATURE_LEVEL requested[] = {D3D_FEATURE_LEVEL_11_0};
    D3D_FEATURE_LEVEL actual = D3D_FEATURE_LEVEL_11_0;
    HRESULT deviceResult = D3D11CreateDevice(
        nullptr,
        D3D_DRIVER_TYPE_WARP,
        nullptr,
        0,
        requested,
        1,
        D3D11_SDK_VERSION,
        &device,
        &actual,
        &context);
    if (FAILED(deviceResult))
        return 2;

    ID3D11VertexShader* vertex = nullptr;
    ID3D11PixelShader* pixel = nullptr;
    HRESULT vertexResult = device->CreateVertexShader(
        g_EndfieldM27VertexDxbc,
        g_EndfieldM27VertexDxbcSize,
        nullptr,
        &vertex);
    HRESULT pixelResult = device->CreatePixelShader(
        g_EndfieldM27PixelDxbc,
        g_EndfieldM27PixelDxbcSize,
        nullptr,
        &pixel);
    ID3D11VertexShader* m14Vertex = nullptr;
    HRESULT m14VertexResult = device->CreateVertexShader(
        g_EndfieldM14VertexDxbc,
        g_EndfieldM14VertexDxbcSize,
        nullptr,
        &m14Vertex);
    ID3D11PixelShader* m14Pixel = nullptr;
    HRESULT m14PixelResult = device->CreatePixelShader(
        g_EndfieldM14PixelDxbc,
        g_EndfieldM14PixelDxbcSize,
        nullptr,
        &m14Pixel);
    std::printf(
        "registry_ready=%u dispatch=%u m14_dispatch=%u hashes=%u "
        "vertex=0x%08lx pixel=0x%08lx m14_vertex=0x%08lx m14_pixel=0x%08lx\n",
        EndfieldM27Substitution::Ready() ? 1u : 0u,
        dispatchValid ? 1u : 0u,
        m14DispatchValid ? 1u : 0u,
        hashesValid ? 1u : 0u,
        static_cast<unsigned long>(vertexResult),
        static_cast<unsigned long>(pixelResult),
        static_cast<unsigned long>(m14VertexResult),
        static_cast<unsigned long>(m14PixelResult));

    if (m14Pixel != nullptr)
        m14Pixel->Release();
    if (m14Vertex != nullptr)
        m14Vertex->Release();
    if (pixel != nullptr)
        pixel->Release();
    if (vertex != nullptr)
        vertex->Release();
    context->Release();
    device->Release();
    return hashesValid && dispatchValid && m14DispatchValid &&
            SUCCEEDED(vertexResult) && SUCCEEDED(pixelResult) &&
            SUCCEEDED(m14VertexResult) && SUCCEEDED(m14PixelResult)
        ? 0
        : 3;
}
