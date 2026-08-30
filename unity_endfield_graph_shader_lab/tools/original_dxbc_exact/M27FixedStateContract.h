#pragma once

#include <d3d11.h>

namespace EndfieldM27FixedState
{
inline D3D11_DEPTH_STENCIL_DESC DepthStencil()
{
    D3D11_DEPTH_STENCIL_DESC value = {};
    value.DepthEnable = TRUE;
    value.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ALL;
    value.DepthFunc = D3D11_COMPARISON_GREATER_EQUAL;
    value.StencilEnable = TRUE;
    value.StencilReadMask = D3D11_DEFAULT_STENCIL_READ_MASK;
    value.StencilWriteMask = D3D11_DEFAULT_STENCIL_WRITE_MASK;
    value.FrontFace.StencilFailOp = D3D11_STENCIL_OP_KEEP;
    value.FrontFace.StencilDepthFailOp = D3D11_STENCIL_OP_KEEP;
    value.FrontFace.StencilPassOp = D3D11_STENCIL_OP_REPLACE;
    value.FrontFace.StencilFunc = D3D11_COMPARISON_ALWAYS;
    value.BackFace = value.FrontFace;
    return value;
}

inline D3D11_RASTERIZER_DESC Rasterizer()
{
    D3D11_RASTERIZER_DESC value = {};
    value.FillMode = D3D11_FILL_SOLID;
    value.CullMode = D3D11_CULL_BACK;
    value.FrontCounterClockwise = TRUE;
    value.DepthClipEnable = TRUE;
    value.ScissorEnable = TRUE;
    return value;
}
}
