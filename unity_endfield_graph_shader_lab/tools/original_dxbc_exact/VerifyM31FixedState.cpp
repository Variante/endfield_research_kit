#include <d3d11.h>
#include <cstdio>

#include "M31FixedStateContract.h"

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

    ID3D11SamplerState* samplers[2] = {};
    ID3D11BlendState* blend = nullptr;
    ID3D11DepthStencilState* depth = nullptr;
    ID3D11RasterizerState* rasterizer = nullptr;
    ID3D11Texture2D* depthTexture = nullptr;
    ID3D11DepthStencilView* depthView = nullptr;
    ID3D11ShaderResourceView* depthSrv = nullptr;
    bool valid = true;

    for (UINT slot = 0; slot < 2; ++slot)
    {
        D3D11_SAMPLER_DESC description =
            EndfieldM31FixedState::Sampler(slot);
        valid &= SUCCEEDED(device->CreateSamplerState(
            &description, &samplers[slot]));
    }
    D3D11_BLEND_DESC blendDescription = EndfieldM31FixedState::Blend();
    valid &= SUCCEEDED(device->CreateBlendState(&blendDescription, &blend));
    D3D11_DEPTH_STENCIL_DESC depthDescription =
        EndfieldM31FixedState::DepthStencil();
    valid &= SUCCEEDED(device->CreateDepthStencilState(
        &depthDescription, &depth));
    D3D11_RASTERIZER_DESC rasterizerDescription =
        EndfieldM31FixedState::Rasterizer();
    valid &= SUCCEEDED(device->CreateRasterizerState(
        &rasterizerDescription, &rasterizer));

    D3D11_TEXTURE2D_DESC textureDescription = {};
    textureDescription.Width = 64u;
    textureDescription.Height = 64u;
    textureDescription.MipLevels = 1u;
    textureDescription.ArraySize = 1u;
    textureDescription.Format = DXGI_FORMAT_R32G8X24_TYPELESS;
    textureDescription.SampleDesc.Count = 1u;
    textureDescription.Usage = D3D11_USAGE_DEFAULT;
    textureDescription.BindFlags = D3D11_BIND_DEPTH_STENCIL |
        D3D11_BIND_SHADER_RESOURCE;
    valid &= SUCCEEDED(device->CreateTexture2D(
        &textureDescription, nullptr, &depthTexture));
    D3D11_DEPTH_STENCIL_VIEW_DESC dsvDescription =
        EndfieldM31FixedState::ReadOnlyDepthView();
    valid &= depthTexture != nullptr && SUCCEEDED(device->CreateDepthStencilView(
        depthTexture, &dsvDescription, &depthView));
    D3D11_SHADER_RESOURCE_VIEW_DESC srvDescription = {};
    srvDescription.Format = DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS;
    srvDescription.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
    srvDescription.Texture2D.MostDetailedMip = 0u;
    srvDescription.Texture2D.MipLevels = 1u;
    valid &= depthTexture != nullptr && SUCCEEDED(device->CreateShaderResourceView(
        depthTexture, &srvDescription, &depthSrv));

    D3D11_BLEND_DESC actualBlend = {};
    if (blend != nullptr) blend->GetDesc(&actualBlend);
    D3D11_DEPTH_STENCIL_DESC actualDepth = {};
    if (depth != nullptr) depth->GetDesc(&actualDepth);
    D3D11_RASTERIZER_DESC actualRasterizer = {};
    if (rasterizer != nullptr) rasterizer->GetDesc(&actualRasterizer);
    D3D11_DEPTH_STENCIL_VIEW_DESC actualDsv = {};
    if (depthView != nullptr) depthView->GetDesc(&actualDsv);
    D3D11_SAMPLER_DESC actualSampler0 = {};
    D3D11_SAMPLER_DESC actualSampler1 = {};
    if (samplers[0] != nullptr) samplers[0]->GetDesc(&actualSampler0);
    if (samplers[1] != nullptr) samplers[1]->GetDesc(&actualSampler1);

    valid &= actualSampler0.Filter == D3D11_FILTER_MIN_MAG_MIP_POINT &&
        actualSampler0.AddressU == D3D11_TEXTURE_ADDRESS_CLAMP &&
        actualSampler0.MaxLOD == 1000.0f &&
        actualSampler1.Filter == D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT &&
        actualSampler1.AddressU == D3D11_TEXTURE_ADDRESS_WRAP &&
        actualSampler1.MaxLOD == 1000.0f;
    const D3D11_RENDER_TARGET_BLEND_DESC& color = actualBlend.RenderTarget[0];
    const D3D11_RENDER_TARGET_BLEND_DESC& motion = actualBlend.RenderTarget[1];
    valid &= !actualBlend.AlphaToCoverageEnable &&
        actualBlend.IndependentBlendEnable && color.BlendEnable &&
        color.SrcBlend == D3D11_BLEND_ONE &&
        color.DestBlend == D3D11_BLEND_INV_SRC_ALPHA &&
        motion.BlendEnable && motion.SrcBlend == D3D11_BLEND_SRC_COLOR &&
        motion.DestBlend == D3D11_BLEND_INV_SRC_COLOR &&
        motion.SrcBlendAlpha == D3D11_BLEND_ONE &&
        motion.DestBlendAlpha == D3D11_BLEND_ONE;
    valid &= actualDepth.DepthEnable &&
        actualDepth.DepthWriteMask == D3D11_DEPTH_WRITE_MASK_ZERO &&
        actualDepth.DepthFunc == D3D11_COMPARISON_GREATER_EQUAL &&
        actualDepth.StencilEnable && actualDepth.StencilReadMask == 0xffu &&
        actualDepth.StencilWriteMask == 0xffu &&
        actualDepth.FrontFace.StencilPassOp == D3D11_STENCIL_OP_KEEP &&
        actualDepth.FrontFace.StencilFunc == D3D11_COMPARISON_ALWAYS &&
        actualDepth.BackFace.StencilFunc == D3D11_COMPARISON_ALWAYS;
    valid &= actualRasterizer.FillMode == D3D11_FILL_SOLID &&
        actualRasterizer.CullMode == D3D11_CULL_NONE &&
        actualRasterizer.FrontCounterClockwise &&
        actualRasterizer.DepthClipEnable && actualRasterizer.ScissorEnable &&
        actualRasterizer.DepthBias == 0 &&
        actualRasterizer.DepthBiasClamp == 0.0f &&
        actualRasterizer.SlopeScaledDepthBias == 0.0f &&
        !actualRasterizer.MultisampleEnable &&
        !actualRasterizer.AntialiasedLineEnable;
    valid &= actualDsv.Format == DXGI_FORMAT_D32_FLOAT_S8X24_UINT &&
        actualDsv.ViewDimension == D3D11_DSV_DIMENSION_TEXTURE2D &&
        actualDsv.Flags == (D3D11_DSV_READ_ONLY_DEPTH |
                            D3D11_DSV_READ_ONLY_STENCIL);

    if (valid)
    {
        context->OMSetRenderTargets(0, nullptr, depthView);
        context->PSSetShaderResources(0, 1, &depthSrv);
        ID3D11ShaderResourceView* observed = nullptr;
        context->PSGetShaderResources(0, 1, &observed);
        valid = observed != nullptr;
        Release(observed);
        ID3D11ShaderResourceView* clear = nullptr;
        context->PSSetShaderResources(0, 1, &clear);
        context->OMSetRenderTargets(0, nullptr, nullptr);
    }

    std::printf(
        "feature_level=0x%x states=%d independent=%d rtv1=%u/%u "
        "depth=%u stencil=%d dsv_flags=%u simultaneous_depth_srv=%d\n",
        static_cast<unsigned>(featureLevel), valid ? 1 : 0,
        actualBlend.IndependentBlendEnable ? 1 : 0,
        static_cast<unsigned>(motion.SrcBlend),
        static_cast<unsigned>(motion.DestBlend),
        static_cast<unsigned>(actualDepth.DepthFunc),
        actualDepth.StencilEnable ? 1 : 0,
        static_cast<unsigned>(actualDsv.Flags), valid ? 1 : 0);

    Release(depthSrv);
    Release(depthView);
    Release(depthTexture);
    Release(rasterizer);
    Release(depth);
    Release(blend);
    Release(samplers[1]);
    Release(samplers[0]);
    Release(context);
    Release(device);
    return valid ? 0 : 20;
}
