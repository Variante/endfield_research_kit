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
        std::memcmp(digest, g_EndfieldM27PixelDxbcSha256, 32) == 0;

    unsigned char unknownShellHash[32] = {};
    unknownShellHash[0] = 1;
    const bool failsClosed =
        !EndfieldM27Substitution::Ready() &&
        EndfieldM27Substitution::Resolve(
            EndfieldM27Substitution::Stage::Vertex,
            unknownShellHash) == nullptr &&
        EndfieldM27Substitution::Resolve(
            EndfieldM27Substitution::Stage::Pixel,
            unknownShellHash) == nullptr;

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
    std::printf(
        "registry_ready=%u fail_closed=%u hashes=%u vertex=0x%08lx pixel=0x%08lx\n",
        EndfieldM27Substitution::Ready() ? 1u : 0u,
        failsClosed ? 1u : 0u,
        hashesValid ? 1u : 0u,
        static_cast<unsigned long>(vertexResult),
        static_cast<unsigned long>(pixelResult));

    if (pixel != nullptr)
        pixel->Release();
    if (vertex != nullptr)
        vertex->Release();
    context->Release();
    device->Release();
    return hashesValid && failsClosed &&
            SUCCEEDED(vertexResult) && SUCCEEDED(pixelResult)
        ? 0
        : 3;
}
