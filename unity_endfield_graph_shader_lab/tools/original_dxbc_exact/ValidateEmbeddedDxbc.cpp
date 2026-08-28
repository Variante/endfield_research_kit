#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <d3d11.h>

#include <cstdio>

#include "EmbeddedDxbc.generated.h"
#include "M13CapturePayload.generated.h"
#include "M21PeakCapturePayload.generated.h"

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
    ID3D11VertexShader* m27Vertex = nullptr;
    HRESULT m27VertexResult = device->CreateVertexShader(
        g_EndfieldM27VertexDxbc,
        g_EndfieldM27VertexDxbcSize,
        nullptr,
        &m27Vertex);
    ID3D11PixelShader* m27Pixel = nullptr;
    HRESULT m27PixelResult = device->CreatePixelShader(
        g_EndfieldM27PixelDxbc,
        g_EndfieldM27PixelDxbcSize,
        nullptr,
        &m27Pixel);
    const D3D11_INPUT_ELEMENT_DESC m27Elements60[] = {
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
    ID3D11InputLayout* m27InputLayout60 = nullptr;
    HRESULT m27InputLayout60Result = device->CreateInputLayout(
        m27Elements60,
        static_cast<UINT>(sizeof(m27Elements60) / sizeof(m27Elements60[0])),
        g_EndfieldM27VertexDxbc,
        g_EndfieldM27VertexDxbcSize,
        &m27InputLayout60);
    const D3D11_INPUT_ELEMENT_DESC m27Elements68[] = {
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
    ID3D11InputLayout* m27InputLayout68 = nullptr;
    HRESULT m27InputLayout68Result = device->CreateInputLayout(
        m27Elements68,
        static_cast<UINT>(sizeof(m27Elements68) / sizeof(m27Elements68[0])),
        g_EndfieldM27VertexDxbc,
        g_EndfieldM27VertexDxbcSize,
        &m27InputLayout68);
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
    ID3D11VertexShader* m13Vertex = nullptr;
    HRESULT m13VertexResult = device->CreateVertexShader(
        g_EndfieldM13VertexDxbc,
        g_EndfieldM13VertexDxbcSize,
        nullptr,
        &m13Vertex);
    ID3D11PixelShader* m13Pixel = nullptr;
    HRESULT m13PixelResult = device->CreatePixelShader(
        g_EndfieldM13PixelDxbc,
        g_EndfieldM13PixelDxbcSize,
        nullptr,
        &m13Pixel);
    const D3D11_INPUT_ELEMENT_DESC m13Elements[] = {
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
    ID3D11InputLayout* m13InputLayout = nullptr;
    HRESULT m13InputLayoutResult = device->CreateInputLayout(
        m13Elements,
        static_cast<UINT>(sizeof(m13Elements) / sizeof(m13Elements[0])),
        g_EndfieldM13VertexDxbc,
        g_EndfieldM13VertexDxbcSize,
        &m13InputLayout);
    ID3D11VertexShader* m21Vertex = nullptr;
    HRESULT m21VertexResult = device->CreateVertexShader(
        g_EndfieldM21PeakVertexDxbc,
        g_EndfieldM21PeakVertexDxbcSize,
        nullptr,
        &m21Vertex);
    ID3D11PixelShader* m21Pixel = nullptr;
    HRESULT m21PixelResult = device->CreatePixelShader(
        g_EndfieldM21PeakPixelDxbc,
        g_EndfieldM21PeakPixelDxbcSize,
        nullptr,
        &m21Pixel);
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
    ID3D11InputLayout* m21InputLayout = nullptr;
    HRESULT m21InputLayoutResult = device->CreateInputLayout(
        m21Elements,
        static_cast<UINT>(sizeof(m21Elements) / sizeof(m21Elements[0])),
        g_EndfieldM21PeakVertexDxbc,
        g_EndfieldM21PeakVertexDxbcSize,
        &m21InputLayout);
    ID3D11Texture2D* m13Texture = nullptr;
    const auto& texturePayload = g_EndfieldM13Textures[0];
    D3D11_TEXTURE2D_DESC textureDescription = {};
    textureDescription.Width = texturePayload.width;
    textureDescription.Height = texturePayload.height;
    textureDescription.MipLevels = 1;
    textureDescription.ArraySize = 1;
    textureDescription.Format = DXGI_FORMAT_BC7_UNORM_SRGB;
    textureDescription.SampleDesc.Count = 1;
    textureDescription.Usage = D3D11_USAGE_IMMUTABLE;
    textureDescription.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA textureInitial = {};
    textureInitial.pSysMem = texturePayload.bytes;
    textureInitial.SysMemPitch = texturePayload.width * 4u;
    textureInitial.SysMemSlicePitch = static_cast<UINT>(texturePayload.size);
    HRESULT m13TextureResult = device->CreateTexture2D(
        &textureDescription, &textureInitial, &m13Texture);
    ID3D11VertexShader* uberVertex = nullptr;
    HRESULT uberVertexResult = device->CreateVertexShader(
        g_EndfieldUberVertexDxbc,
        g_EndfieldUberVertexDxbcSize,
        nullptr,
        &uberVertex);
    ID3D11PixelShader* uberPixel = nullptr;
    HRESULT uberPixelResult = device->CreatePixelShader(
        g_EndfieldUberPixelDxbc,
        g_EndfieldUberPixelDxbcSize,
        nullptr,
        &uberPixel);

    std::printf(
        "feature_level=0x%x vertex=0x%08lx pixel=0x%08lx "
        "m27_vertex=0x%08lx m27_pixel=0x%08lx m27_layout60=0x%08lx "
        "m27_layout68=0x%08lx "
        "m14_vertex=0x%08lx m14_pixel=0x%08lx m14_layout=0x%08lx "
        "m13_vertex=0x%08lx m13_pixel=0x%08lx m13_layout=0x%08lx "
        "m13_bc7=0x%08lx m21_vertex=0x%08lx m21_pixel=0x%08lx "
        "m21_layout=0x%08lx uber_vertex=0x%08lx uber_pixel=0x%08lx\n",
        static_cast<unsigned int>(featureLevel),
        static_cast<unsigned long>(vertexResult),
        static_cast<unsigned long>(pixelResult),
        static_cast<unsigned long>(m27VertexResult),
        static_cast<unsigned long>(m27PixelResult),
        static_cast<unsigned long>(m27InputLayout60Result),
        static_cast<unsigned long>(m27InputLayout68Result),
        static_cast<unsigned long>(m14VertexResult),
        static_cast<unsigned long>(m14PixelResult),
        static_cast<unsigned long>(m14InputLayoutResult),
        static_cast<unsigned long>(m13VertexResult),
        static_cast<unsigned long>(m13PixelResult),
        static_cast<unsigned long>(m13InputLayoutResult),
        static_cast<unsigned long>(m13TextureResult),
        static_cast<unsigned long>(m21VertexResult),
        static_cast<unsigned long>(m21PixelResult),
        static_cast<unsigned long>(m21InputLayoutResult),
        static_cast<unsigned long>(uberVertexResult),
        static_cast<unsigned long>(uberPixelResult));

    if (pixel != nullptr)
        pixel->Release();
    if (m27InputLayout68 != nullptr)
        m27InputLayout68->Release();
    if (m27InputLayout60 != nullptr)
        m27InputLayout60->Release();
    if (m27Pixel != nullptr)
        m27Pixel->Release();
    if (m27Vertex != nullptr)
        m27Vertex->Release();
    if (m14Pixel != nullptr)
        m14Pixel->Release();
    if (m14InputLayout != nullptr)
        m14InputLayout->Release();
    if (m14Vertex != nullptr)
        m14Vertex->Release();
    if (m13Texture != nullptr)
        m13Texture->Release();
    if (m13InputLayout != nullptr)
        m13InputLayout->Release();
    if (m13Pixel != nullptr)
        m13Pixel->Release();
    if (m13Vertex != nullptr)
        m13Vertex->Release();
    if (m21InputLayout != nullptr)
        m21InputLayout->Release();
    if (m21Pixel != nullptr)
        m21Pixel->Release();
    if (m21Vertex != nullptr)
        m21Vertex->Release();
    if (uberPixel != nullptr)
        uberPixel->Release();
    if (uberVertex != nullptr)
        uberVertex->Release();
    if (vertex != nullptr)
        vertex->Release();
    context->Release();
    device->Release();
    return SUCCEEDED(vertexResult) && SUCCEEDED(pixelResult) &&
            SUCCEEDED(m27VertexResult) && SUCCEEDED(m27PixelResult) &&
            SUCCEEDED(m27InputLayout60Result) &&
            SUCCEEDED(m27InputLayout68Result) &&
            SUCCEEDED(m14VertexResult) && SUCCEEDED(m14PixelResult)
            && SUCCEEDED(m14InputLayoutResult) && SUCCEEDED(m13VertexResult)
            && SUCCEEDED(m13PixelResult) && SUCCEEDED(m13InputLayoutResult)
            && SUCCEEDED(m13TextureResult) && SUCCEEDED(m21VertexResult)
            && SUCCEEDED(m21PixelResult) && SUCCEEDED(m21InputLayoutResult)
            && SUCCEEDED(uberVertexResult)
            && SUCCEEDED(uberPixelResult)
        ? 0
        : 3;
}
