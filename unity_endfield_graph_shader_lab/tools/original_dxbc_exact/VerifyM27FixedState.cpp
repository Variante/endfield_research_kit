#include <d3d11.h>
#include <cstdio>

#include "M27FixedStateContract.h"

template <typename T>
void Release(T*& value)
{
    if (value != nullptr)
    {
        value->Release();
        value = nullptr;
    }
}

int main()
{
    ID3D11Device* device = nullptr;
    ID3D11DeviceContext* context = nullptr;
    D3D_FEATURE_LEVEL featureLevel = {};
    HRESULT result = D3D11CreateDevice(
        nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0, nullptr, 0,
        D3D11_SDK_VERSION, &device, &featureLevel, &context);
    if (FAILED(result)) return 10;

    D3D11_DEPTH_STENCIL_DESC depthDescription =
        EndfieldM27FixedState::DepthStencil();
    D3D11_RASTERIZER_DESC rasterizerDescription =
        EndfieldM27FixedState::Rasterizer();
    ID3D11DepthStencilState* depth = nullptr;
    ID3D11RasterizerState* rasterizer = nullptr;
    bool valid = SUCCEEDED(device->CreateDepthStencilState(
        &depthDescription, &depth));
    valid &= SUCCEEDED(device->CreateRasterizerState(
        &rasterizerDescription, &rasterizer));

    D3D11_DEPTH_STENCIL_DESC actualDepth = {};
    D3D11_RASTERIZER_DESC actualRasterizer = {};
    if (depth != nullptr) depth->GetDesc(&actualDepth);
    if (rasterizer != nullptr) rasterizer->GetDesc(&actualRasterizer);
    valid &= actualDepth.DepthEnable &&
        actualDepth.DepthWriteMask == D3D11_DEPTH_WRITE_MASK_ALL &&
        actualDepth.DepthFunc == D3D11_COMPARISON_GREATER_EQUAL &&
        actualDepth.StencilEnable &&
        actualDepth.StencilReadMask == D3D11_DEFAULT_STENCIL_READ_MASK &&
        actualDepth.StencilWriteMask == D3D11_DEFAULT_STENCIL_WRITE_MASK &&
        actualDepth.FrontFace.StencilFailOp == D3D11_STENCIL_OP_KEEP &&
        actualDepth.FrontFace.StencilDepthFailOp == D3D11_STENCIL_OP_KEEP &&
        actualDepth.FrontFace.StencilPassOp == D3D11_STENCIL_OP_REPLACE &&
        actualDepth.FrontFace.StencilFunc == D3D11_COMPARISON_ALWAYS &&
        actualDepth.BackFace.StencilFailOp == D3D11_STENCIL_OP_KEEP &&
        actualDepth.BackFace.StencilDepthFailOp == D3D11_STENCIL_OP_KEEP &&
        actualDepth.BackFace.StencilPassOp == D3D11_STENCIL_OP_REPLACE &&
        actualDepth.BackFace.StencilFunc == D3D11_COMPARISON_ALWAYS;
    valid &= actualRasterizer.FillMode == D3D11_FILL_SOLID &&
        actualRasterizer.CullMode == D3D11_CULL_BACK &&
        actualRasterizer.FrontCounterClockwise &&
        actualRasterizer.DepthBias == 0 &&
        actualRasterizer.DepthBiasClamp == 0.0f &&
        actualRasterizer.SlopeScaledDepthBias == 0.0f &&
        actualRasterizer.DepthClipEnable &&
        actualRasterizer.ScissorEnable &&
        !actualRasterizer.MultisampleEnable &&
        !actualRasterizer.AntialiasedLineEnable;

    ID3D11DepthStencilState* observedDepth = nullptr;
    ID3D11RasterizerState* observedRasterizer = nullptr;
    UINT observedReference = ~0u;
    if (valid)
    {
        context->OMSetDepthStencilState(depth, 0u);
        context->RSSetState(rasterizer);
        context->OMGetDepthStencilState(&observedDepth, &observedReference);
        context->RSGetState(&observedRasterizer);
        valid = observedDepth == depth && observedReference == 0u &&
            observedRasterizer == rasterizer;
    }

    std::printf(
        "feature_level=0x%x states=%d depth_write=%u depth_func=%u "
        "cull=%u front_ccw=%d scissor=%d\n",
        static_cast<unsigned>(featureLevel), valid ? 1 : 0,
        static_cast<unsigned>(actualDepth.DepthWriteMask),
        static_cast<unsigned>(actualDepth.DepthFunc),
        static_cast<unsigned>(actualRasterizer.CullMode),
        actualRasterizer.FrontCounterClockwise ? 1 : 0,
        actualRasterizer.ScissorEnable ? 1 : 0);

    Release(observedRasterizer);
    Release(observedDepth);
    Release(rasterizer);
    Release(depth);
    Release(context);
    Release(device);
    return valid ? 0 : 20;
}
