#pragma once

#include <d3d11.h>

namespace EndfieldM31FixedState
{
inline D3D11_SAMPLER_DESC Sampler(UINT slot)
{
    D3D11_SAMPLER_DESC value = {};
    value.Filter = slot == 0u
        ? D3D11_FILTER_MIN_MAG_MIP_POINT
        : D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT;
    value.AddressU = slot == 0u
        ? D3D11_TEXTURE_ADDRESS_CLAMP
        : D3D11_TEXTURE_ADDRESS_WRAP;
    value.AddressV = value.AddressU;
    value.AddressW = value.AddressU;
    value.ComparisonFunc = D3D11_COMPARISON_NEVER;
    value.MaxAnisotropy = 1u;
    value.MinLOD = 0.0f;
    value.MaxLOD = 1000.0f;
    return value;
}

inline D3D11_BLEND_DESC Blend()
{
    D3D11_BLEND_DESC value = {};
    value.AlphaToCoverageEnable = FALSE;
    value.IndependentBlendEnable = TRUE;
    for (UINT target = 0u; target < D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT;
         ++target)
    {
        D3D11_RENDER_TARGET_BLEND_DESC& row = value.RenderTarget[target];
        row.BlendEnable = FALSE;
        row.SrcBlend = D3D11_BLEND_ONE;
        row.DestBlend = D3D11_BLEND_ZERO;
        row.BlendOp = D3D11_BLEND_OP_ADD;
        row.SrcBlendAlpha = D3D11_BLEND_ONE;
        row.DestBlendAlpha = D3D11_BLEND_ZERO;
        row.BlendOpAlpha = D3D11_BLEND_OP_ADD;
        row.RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
    }
    D3D11_RENDER_TARGET_BLEND_DESC& color = value.RenderTarget[0];
    color.BlendEnable = TRUE;
    color.SrcBlend = D3D11_BLEND_ONE;
    color.DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
    color.BlendOp = D3D11_BLEND_OP_ADD;
    color.SrcBlendAlpha = D3D11_BLEND_ONE;
    color.DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
    color.BlendOpAlpha = D3D11_BLEND_OP_ADD;
    color.RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
    D3D11_RENDER_TARGET_BLEND_DESC& motion = value.RenderTarget[1];
    motion.BlendEnable = TRUE;
    motion.SrcBlend = D3D11_BLEND_SRC_COLOR;
    motion.DestBlend = D3D11_BLEND_INV_SRC_COLOR;
    motion.BlendOp = D3D11_BLEND_OP_ADD;
    motion.SrcBlendAlpha = D3D11_BLEND_ONE;
    motion.DestBlendAlpha = D3D11_BLEND_ONE;
    motion.BlendOpAlpha = D3D11_BLEND_OP_ADD;
    motion.RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
    return value;
}

inline D3D11_DEPTH_STENCIL_DESC DepthStencil()
{
    D3D11_DEPTH_STENCIL_DESC value = {};
    value.DepthEnable = TRUE;
    value.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
    value.DepthFunc = D3D11_COMPARISON_GREATER_EQUAL;
    value.StencilEnable = TRUE;
    value.StencilReadMask = 0xffu;
    value.StencilWriteMask = 0xffu;
    value.FrontFace.StencilFailOp = D3D11_STENCIL_OP_KEEP;
    value.FrontFace.StencilDepthFailOp = D3D11_STENCIL_OP_KEEP;
    value.FrontFace.StencilPassOp = D3D11_STENCIL_OP_KEEP;
    value.FrontFace.StencilFunc = D3D11_COMPARISON_ALWAYS;
    value.BackFace = value.FrontFace;
    return value;
}

inline D3D11_RASTERIZER_DESC Rasterizer()
{
    D3D11_RASTERIZER_DESC value = {};
    value.FillMode = D3D11_FILL_SOLID;
    value.CullMode = D3D11_CULL_NONE;
    value.FrontCounterClockwise = TRUE;
    value.DepthClipEnable = TRUE;
    value.ScissorEnable = TRUE;
    return value;
}

inline D3D11_DEPTH_STENCIL_VIEW_DESC ReadOnlyDepthView()
{
    D3D11_DEPTH_STENCIL_VIEW_DESC value = {};
    value.Format = DXGI_FORMAT_D32_FLOAT_S8X24_UINT;
    value.ViewDimension = D3D11_DSV_DIMENSION_TEXTURE2D;
    value.Flags = D3D11_DSV_READ_ONLY_DEPTH |
        D3D11_DSV_READ_ONLY_STENCIL;
    value.Texture2D.MipSlice = 0u;
    return value;
}
}
