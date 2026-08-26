#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <d3d11.h>

#include <cstdio>

#include "EmbeddedDxbc.generated.h"

int main()
{
    ID3D11Device* device = nullptr;
    ID3D11DeviceContext* context = nullptr;
    D3D_FEATURE_LEVEL featureLevel = D3D_FEATURE_LEVEL_11_0;
    const D3D_FEATURE_LEVEL requested[] = {D3D_FEATURE_LEVEL_11_0};
    HRESULT createResult = D3D11CreateDevice(
        nullptr,
        D3D_DRIVER_TYPE_WARP,
        nullptr,
        0,
        requested,
        1,
        D3D11_SDK_VERSION,
        &device,
        &featureLevel,
        &context);
    if (FAILED(createResult))
    {
        std::printf("device=0x%08lx\n", static_cast<unsigned long>(createResult));
        return 2;
    }

    ID3D11VertexShader* vertex = nullptr;
    HRESULT vertexResult = device->CreateVertexShader(
        g_EndfieldSelectedVertexDxbc,
        g_EndfieldSelectedVertexDxbcSize,
        nullptr,
        &vertex);
    ID3D11PixelShader* pixel = nullptr;
    HRESULT pixelResult = device->CreatePixelShader(
        g_EndfieldSelectedPixelDxbc,
        g_EndfieldSelectedPixelDxbcSize,
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
    const D3D11_INPUT_ELEMENT_DESC m14Elements[] = {
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
    ID3D11InputLayout* m14InputLayout = nullptr;
    HRESULT m14InputLayoutResult = device->CreateInputLayout(
        m14Elements,
        static_cast<UINT>(sizeof(m14Elements) / sizeof(m14Elements[0])),
        g_EndfieldM14VertexDxbc,
        g_EndfieldM14VertexDxbcSize,
        &m14InputLayout);

    std::printf(
        "feature_level=0x%x vertex=0x%08lx pixel=0x%08lx "
        "m14_vertex=0x%08lx m14_pixel=0x%08lx m14_layout=0x%08lx\n",
        static_cast<unsigned int>(featureLevel),
        static_cast<unsigned long>(vertexResult),
        static_cast<unsigned long>(pixelResult),
        static_cast<unsigned long>(m14VertexResult),
        static_cast<unsigned long>(m14PixelResult),
        static_cast<unsigned long>(m14InputLayoutResult));

    if (pixel != nullptr)
        pixel->Release();
    if (m14Pixel != nullptr)
        m14Pixel->Release();
    if (m14InputLayout != nullptr)
        m14InputLayout->Release();
    if (m14Vertex != nullptr)
        m14Vertex->Release();
    if (vertex != nullptr)
        vertex->Release();
    context->Release();
    device->Release();
    return SUCCEEDED(vertexResult) && SUCCEEDED(pixelResult) &&
            SUCCEEDED(m14VertexResult) && SUCCEEDED(m14PixelResult)
            && SUCCEEDED(m14InputLayoutResult)
        ? 0
        : 3;
}
