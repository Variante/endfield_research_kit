#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <d3d11.h>

#include <cstdint>
#include <cstdio>

struct EndfieldM23DxbcValidation {
    std::uint32_t shaderMask;
    std::uint32_t inputLayoutMask;
    std::uint32_t vertexBufferMask;
    std::uint32_t vertexConstantBufferMask;
    std::uint32_t pixelConstantBufferMask;
    std::uint32_t shaderResourceMask;
    std::uint32_t samplerMask;
    std::uint32_t stateMask;
};

extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidate(
    ID3D11Device*, EndfieldM23DxbcValidation*);

int main() {
    ID3D11Device* device = nullptr;
    ID3D11DeviceContext* context = nullptr;
    D3D_FEATURE_LEVEL featureLevel = D3D_FEATURE_LEVEL_11_0;
    const D3D_FEATURE_LEVEL requested[] = {D3D_FEATURE_LEVEL_11_0};
    HRESULT hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0,
                                   requested, 1, D3D11_SDK_VERSION,
                                   &device, &featureLevel, &context);
    if (FAILED(hr)) {
        std::printf("device=0x%08lx\n", static_cast<unsigned long>(hr));
        return 2;
    }

    EndfieldM23DxbcValidation report = {};
    hr = EndfieldOriginalM23DxbcValidate(device, &report);
    std::printf(
        "feature_level=0x%x result=0x%08lx shaders=0x%x input=0x%x vb=0x%x "
        "vs_cb_creation=0x%x ps_cb_creation=0x%x srv_creation=0x%x "
        "sampler_creation=0x%x states=0x%x\n",
        static_cast<unsigned int>(featureLevel), static_cast<unsigned long>(hr),
        report.shaderMask, report.inputLayoutMask, report.vertexBufferMask,
        report.vertexConstantBufferMask, report.pixelConstantBufferMask,
        report.shaderResourceMask, report.samplerMask, report.stateMask);

    if (context != nullptr) context->Release();
    if (device != nullptr) device->Release();
    const bool complete = SUCCEEDED(hr) && report.shaderMask == 0x3u &&
        report.inputLayoutMask == 0x1u && report.vertexBufferMask == 0x1u &&
        report.vertexConstantBufferMask == 0x1fu &&
        report.pixelConstantBufferMask == 0x1fu &&
        report.shaderResourceMask == 0x1fu && report.samplerMask == 0x1fu &&
        report.stateMask == 0x7u;
    return complete ? 0 : 3;
}
