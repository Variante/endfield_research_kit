#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <d3d11.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>

struct EndfieldM23DxbcValidation {
    std::uint32_t mode;
    std::uint32_t shaderMask;
    std::uint32_t inputLayoutMask;
    std::uint32_t vertexBufferMask;
    std::uint32_t vertexConstantBufferMask;
    std::uint32_t pixelConstantBufferMask;
    std::uint32_t shaderResourceMask;
    std::uint32_t samplerMask;
    std::uint32_t stateMask;
    std::uint32_t vsBindingMask, psBindingMask, inputBindingMask, vertexBindingMask;
    std::uint32_t vsConstantBufferBindingMask, psConstantBufferBindingMask;
    std::uint32_t shaderResourceBindingMask;
    std::uint32_t vertexShaderResourceCreationMask, vertexShaderResourceBindingMask;
    std::uint32_t samplerBindingMask, stateBindingMask;
    std::uint32_t renderTargetBindingMask, topologyBindingMask, viewportBindingMask;
    std::uint32_t drawIssued, readbackFinite, readbackChanged, visualFidelityClaim;
    std::uint32_t diagnosticVsSignatureMask, diagnosticVsSourceHashMask;
    std::uint32_t diagnosticVsCompiledHashMask;
    char diagnosticVsSourceSha256[65];
    char diagnosticVsCompiledSha256[65];
    std::uint32_t namedLowMaterialHashMask, namedLowContractHashMask, namedLowComponentMapMask;
    char namedLowMaterialSha256[65];
    char namedLowContractSha256[65];
    char namedLowComponentMap[1024];
    std::uint32_t readbackChangedFromZero;
    float readback[4];
};

extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidate(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*);
extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidateDiagnosticVs(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*);
extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidateDiagnosticVsNamedLow(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*);

int main(int argc, char** argv) {
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
    const bool namedLow = argc > 2 && std::strcmp(argv[2], "--named-low") == 0;
    const bool diagnosticVs = namedLow || (argc > 2 && std::strcmp(argv[2], "--diagnostic-vs") == 0);
    hr = namedLow ? EndfieldOriginalM23DxbcValidateDiagnosticVsNamedLow(device, context, &report)
                  : (diagnosticVs ? EndfieldOriginalM23DxbcValidateDiagnosticVs(device, context, &report)
                                  : EndfieldOriginalM23DxbcValidate(device, context, &report));
    std::printf(
        "mode=%s feature_level=0x%x result=0x%08lx shaders=0x%x input=0x%x vb=0x%x "
        "vs_cb_creation=0x%x ps_cb_creation=0x%x srv_creation=0x%x "
        "sampler_creation=0x%x states=0x%x vs_bind=0x%x ps_bind=0x%x "
        "input_bind=0x%x vb_bind=0x%x vs_cb_bind=0x%x ps_cb_bind=0x%x "
        "srv_bind=0x%x sampler_bind=0x%x state_bind=0x%x vs_srv_create=0x%x "
        "vs_srv_bind=0x%x rt_bind=0x%x topology=0x%x viewport=0x%x "
        "draw=%u finite=%u changed=%u fidelity=%u readback=[%.9g,%.9g,%.9g,%.9g]\n",
        namedLow ? "diagnostic_vs_exact_ps_named_low" : (diagnosticVs ? "diagnostic_vs_exact_ps" : "exact_pair"),
        static_cast<unsigned int>(featureLevel), static_cast<unsigned long>(hr),
        report.shaderMask, report.inputLayoutMask, report.vertexBufferMask,
        report.vertexConstantBufferMask, report.pixelConstantBufferMask,
        report.shaderResourceMask, report.samplerMask, report.stateMask,
        report.vsBindingMask, report.psBindingMask, report.inputBindingMask,
        report.vertexBindingMask, report.vsConstantBufferBindingMask,
        report.psConstantBufferBindingMask, report.shaderResourceBindingMask,
        report.samplerBindingMask, report.stateBindingMask,
        report.vertexShaderResourceCreationMask,
        report.vertexShaderResourceBindingMask,
        report.renderTargetBindingMask, report.topologyBindingMask,
        report.viewportBindingMask, report.drawIssued,
        report.readbackFinite, report.readbackChanged,
        report.visualFidelityClaim, report.readback[0], report.readback[1],
        report.readback[2], report.readback[3]);

    if (argc > 1) {
        std::ofstream output(argv[1], std::ios::binary | std::ios::trunc);
        output << "{\n"
            << "  \"schema\": \"endfield.original-m23-dxbc-exact.v3\",\n"
            << "  \"mode\": \"" << (namedLow ? "diagnostic_vs_exact_ps_named_low" : (diagnosticVs ? "diagnostic_vs_exact_ps" : "exact_pair")) << "\",\n"
            << "  \"status\": \"" << (SUCCEEDED(hr) ? "pass" : "fail") << "\",\n"
            << "  \"vertex_sha256\": \"7d0a508f7b1e5c9aef0b89489feae97f8669a8cddaba1de0ccc0e26fd0eb2ca0\",\n"
            << "  \"pixel_sha256\": \"0ff508aa08112122c14a3ece17d12f15778eaf39ad0c639c946512dc996b6f83\",\n"
            << "  \"diagnostic_vs_source_sha256\": \"" << report.diagnosticVsSourceSha256 << "\",\n"
            << "  \"diagnostic_vs_signature_mask\": \"0x" << report.diagnosticVsSignatureMask << "\",\n"
            << "  \"diagnostic_vs_source_hash_mask\": \"0x" << report.diagnosticVsSourceHashMask << "\",\n"
            << "  \"diagnostic_vs_compiled_sha256\": \"" << report.diagnosticVsCompiledSha256 << "\",\n"
            << "  \"diagnostic_vs_compiled_hash_mask\": \"0x" << report.diagnosticVsCompiledHashMask << "\",\n"
            << "  \"named_low_material_sha256\": \"" << report.namedLowMaterialSha256 << "\",\n"
            << "  \"named_low_contract_sha256\": \"" << report.namedLowContractSha256 << "\",\n"
            << "  \"named_low_material_hash_mask\": \"0x" << report.namedLowMaterialHashMask << "\",\n"
            << "  \"named_low_contract_hash_mask\": \"0x" << report.namedLowContractHashMask << "\",\n"
            << "  \"named_low_component_map_mask\": \"0x" << report.namedLowComponentMapMask << "\",\n"
            << "  \"named_low_component_map\": \"" << report.namedLowComponentMap << "\",\n"
            << "  \"shader_creation_mask\": \"0x" << std::hex << report.shaderMask << "\",\n"
            << "  \"input_layout_creation_mask\": \"0x" << report.inputLayoutMask << "\",\n"
            << "  \"vertex_buffer_creation_mask\": \"0x" << report.vertexBufferMask << "\",\n"
            << "  \"vs_constant_buffer_creation_mask\": \"0x" << report.vertexConstantBufferMask << "\",\n"
            << "  \"ps_constant_buffer_creation_mask\": \"0x" << report.pixelConstantBufferMask << "\",\n"
            << "  \"shader_resource_creation_mask\": \"0x" << report.shaderResourceMask << "\",\n"
            << "  \"sampler_creation_mask\": \"0x" << report.samplerMask << "\",\n"
            << "  \"state_creation_mask\": \"0x" << report.stateMask << "\",\n"
            << "  \"vs_binding_mask\": \"0x" << report.vsBindingMask << "\",\n"
            << "  \"ps_binding_mask\": \"0x" << report.psBindingMask << "\",\n"
            << "  \"" << (diagnosticVs ? "no_input_layout_binding_mask" : "input_binding_mask")
            << "\": \"0x" << report.inputBindingMask << "\",\n"
            << "  \"" << (diagnosticVs ? "no_vertex_buffer_binding_mask" : "vertex_buffer_binding_mask")
            << "\": \"0x" << report.vertexBindingMask << "\",\n"
            << "  \"vs_constant_buffer_binding_mask\": \"0x" << report.vsConstantBufferBindingMask << "\",\n"
            << "  \"ps_constant_buffer_binding_mask\": \"0x" << report.psConstantBufferBindingMask << "\",\n"
            << "  \"shader_resource_binding_mask\": \"0x" << report.shaderResourceBindingMask << "\",\n"
            << "  \"sampler_binding_mask\": \"0x" << report.samplerBindingMask << "\",\n"
            << "  \"state_binding_mask\": \"0x" << report.stateBindingMask << "\",\n"
            << "  \"vertex_shader_resource_creation_mask\": \"0x" << report.vertexShaderResourceCreationMask << "\",\n"
            << "  \"vertex_shader_resource_binding_mask\": \"0x" << report.vertexShaderResourceBindingMask << "\",\n"
            << "  \"render_target_binding_mask\": \"0x" << report.renderTargetBindingMask << "\",\n"
            << "  \"topology_binding_mask\": \"0x" << report.topologyBindingMask << "\",\n"
            << "  \"viewport_binding_mask\": \"0x" << report.viewportBindingMask << "\",\n"
            << "  \"draw_issued\": " << std::dec << report.drawIssued << ",\n"
            << "  \"readback_finite\": " << report.readbackFinite << ",\n"
            << "  \"readback_changed_from_sentinel\": " << report.readbackChanged << ",\n"
            << "  \"readback_changed_from_zero\": " << report.readbackChangedFromZero << ",\n"
            << "  \"visual_fidelity_claim\": " << report.visualFidelityClaim << ",\n"
            << "  \"b4_high_semantics\": \"zero_or_sentinel_only_non_fidelity\",\n"
            << "  \"readback\": [" << report.readback[0] << "," << report.readback[1] << "," << report.readback[2] << "," << report.readback[3] << "]\n}\n";
    }

    if (context != nullptr) context->Release();
    if (device != nullptr) device->Release();
    const bool common = SUCCEEDED(hr) && report.shaderMask == 0x3u &&
        report.vertexConstantBufferMask == 0x1fu &&
        report.pixelConstantBufferMask == 0x1fu &&
        report.shaderResourceMask == 0x1fu && report.samplerMask == 0x1fu &&
        report.stateMask == 0x7u &&
        report.vsBindingMask == 0x1u && report.psBindingMask == 0x1u &&
        report.inputBindingMask == 0x1u && report.vertexBindingMask == 0x1u &&
        report.vsConstantBufferBindingMask == 0x1fu &&
        report.psConstantBufferBindingMask == 0x1fu &&
        report.shaderResourceBindingMask == 0x1fu &&
        report.samplerBindingMask == 0x1fu &&
        report.stateBindingMask == 0x7u &&
        report.renderTargetBindingMask == 0x1u &&
        report.topologyBindingMask == 0x1u &&
        report.viewportBindingMask == 0x1u && report.drawIssued == 1u &&
        report.readbackFinite == 1u && report.visualFidelityClaim == 0u;
    const bool complete = common && (namedLow
        ? (report.inputLayoutMask == 0u && report.vertexBufferMask == 0u &&
           report.vertexShaderResourceCreationMask == 0u &&
           report.vertexShaderResourceBindingMask == 0u &&
           report.diagnosticVsSignatureMask == 1u && report.diagnosticVsSourceHashMask == 1u &&
           report.diagnosticVsCompiledHashMask == 1u &&
           report.namedLowMaterialHashMask == 1u && report.namedLowContractHashMask == 1u &&
           report.namedLowComponentMapMask == 1u)
        : diagnosticVs
        ? (report.inputLayoutMask == 0u && report.vertexBufferMask == 0u &&
           report.vertexShaderResourceCreationMask == 0u &&
           report.vertexShaderResourceBindingMask == 0u &&
           report.diagnosticVsSignatureMask == 1u &&
           report.diagnosticVsSourceHashMask == 1u &&
           report.diagnosticVsCompiledHashMask == 1u)
        : (report.inputLayoutMask == 0x1u && report.vertexBufferMask == 0x1u &&
           report.vertexShaderResourceCreationMask == 0x1u &&
           report.vertexShaderResourceBindingMask == 0x1u));
    return complete ? 0 : 3;
}
