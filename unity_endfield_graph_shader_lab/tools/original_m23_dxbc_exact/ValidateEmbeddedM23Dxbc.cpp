#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <d3d11.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cmath>
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
    std::uint32_t highProbeExecutionMask, highProbeRegister, highProbeComponent;
    std::uint32_t highBaselineValueMask, highAblationGroupMask;
    std::uint32_t highNeutralDomainMask;
    std::uint32_t diagnosticB2GateMask;
    std::uint32_t highNeutralOverrideMask;
    std::uint32_t syntheticT0ReadbackMask, syntheticT0HashMask;
    char syntheticT0Sha256[65];
    std::uint32_t exactTextureSourceHashMask, exactTextureDecodeMask;
    std::uint32_t exactTextureWidth[5], exactTextureHeight[5];
    std::uint32_t exactTextureVsSignatureMask, exactTextureVsSourceHashMask, exactTextureVsCompiledHashMask;
    char exactTextureVsSourceSha256[65], exactTextureVsCompiledSha256[65];
    std::uint32_t exactTextureGridFinitePixels, exactTextureGridNonzeroPixels, exactTextureGridSize;
    float exactTextureGridMax[4];
    std::uint32_t exactTextureCausalOverrideMask;
    std::uint32_t exactTextureGridRgbNonzeroPixels, exactTextureGridAlphaNonzeroPixels;
    float exactTextureGridRgbMax[3], exactTextureGridRgbMin[3];
    float readback[4];
};

extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidate(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*);
extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidateDiagnosticVs(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*);
extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidateDiagnosticVsNamedLow(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*);
extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidateHighProbe(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*, std::uint32_t, std::uint32_t);
extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidateHighBaseline(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*, std::uint32_t);
extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidateHighNeutral(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*);
extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidateHighNeutralOverride(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*, std::uint32_t);
extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidateExactTexturesNamedLow(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*);
extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidateExactTexturesHighNeutral(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*);
extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidateExactTexturesHighNeutralRgbGate(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*);
extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidateExactTexturesHighNeutralRgbGateWithGrid(
    ID3D11Device*, ID3D11DeviceContext*, EndfieldM23DxbcValidation*, float*, std::uint32_t);

int main(int argc, char** argv) {
    CoInitializeEx(nullptr, COINIT_MULTITHREADED);
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
    const bool highProbe = argc > 2 && std::strcmp(argv[2], "--high-probe") == 0;
    const bool highBaseline = argc > 2 && std::strcmp(argv[2], "--high-baseline") == 0;
    const bool highNeutral = argc > 2 && std::strcmp(argv[2], "--high-neutral") == 0;
    const bool highNeutralOverride = argc > 2 && std::strcmp(argv[2], "--high-neutral-override") == 0;
    const bool exactTexturesNamedLow = argc > 2 && std::strcmp(argv[2], "--exact-textures-named-low") == 0;
    const bool exactTexturesHighNeutral = argc > 2 && std::strcmp(argv[2], "--exact-textures-high-neutral") == 0;
    bool exactTexturesHighNeutralRgb = argc > 2 && std::strcmp(argv[2], "--exact-textures-high-neutral-rgb") == 0;
    const bool exactTexturesHighNeutralRgbGrid = argc > 2 && std::strcmp(argv[2], "--exact-textures-high-neutral-rgb-grid") == 0;
    if (exactTexturesHighNeutralRgbGrid) exactTexturesHighNeutralRgb = true;
    float visualGrid[16 * 16 * 4] = {};
    std::uint32_t neutralOverrideMask = highNeutralOverride && argc > 3 ? static_cast<std::uint32_t>(std::strtoul(argv[3], nullptr, 0)) : 0u;
    std::uint32_t ablationGroupMask = highBaseline && argc > 3 ? static_cast<std::uint32_t>(std::strtoul(argv[3], nullptr, 0)) : 0u;
    std::uint32_t probeRegister = 0, probeComponent = 0;
    char probeChar = 'x';
    if (highProbe && argc > 3 && std::sscanf(argv[3], "b4[%u].%c", &probeRegister, &probeChar) == 2 &&
        (probeChar == 'x' || probeChar == 'y' || probeChar == 'z' || probeChar == 'w')) {
        probeComponent = probeChar == 'x' ? 0u : probeChar == 'y' ? 1u : probeChar == 'z' ? 2u : 3u;
    } else if (highProbe) {
        hr = E_INVALIDARG;
    }
    const bool namedLow = argc > 2 && std::strcmp(argv[2], "--named-low") == 0;
    const bool diagnosticVs = namedLow || highProbe || highBaseline || highNeutral || highNeutralOverride || exactTexturesNamedLow || exactTexturesHighNeutral || exactTexturesHighNeutralRgb || exactTexturesHighNeutralRgbGrid || (argc > 2 && std::strcmp(argv[2], "--diagnostic-vs") == 0);
    if (exactTexturesHighNeutralRgbGrid) hr = EndfieldOriginalM23DxbcValidateExactTexturesHighNeutralRgbGateWithGrid(device, context, &report, visualGrid, 16u * 16u * 4u);
    else if (exactTexturesHighNeutralRgb) hr = EndfieldOriginalM23DxbcValidateExactTexturesHighNeutralRgbGate(device, context, &report);
    else if (exactTexturesNamedLow) hr = EndfieldOriginalM23DxbcValidateExactTexturesNamedLow(device, context, &report);
    else if (exactTexturesHighNeutral) hr = EndfieldOriginalM23DxbcValidateExactTexturesHighNeutral(device, context, &report);
    else if (highNeutralOverride) hr = EndfieldOriginalM23DxbcValidateHighNeutralOverride(device, context, &report, neutralOverrideMask);
    else if (highNeutral) hr = EndfieldOriginalM23DxbcValidateHighNeutral(device, context, &report);
    else if (highBaseline) hr = EndfieldOriginalM23DxbcValidateHighBaseline(device, context, &report, ablationGroupMask);
    else if (highProbe) hr = EndfieldOriginalM23DxbcValidateHighProbe(device, context, &report, probeRegister, probeComponent);
    else if (namedLow) hr = EndfieldOriginalM23DxbcValidateDiagnosticVsNamedLow(device, context, &report);
    else if (diagnosticVs) hr = EndfieldOriginalM23DxbcValidateDiagnosticVs(device, context, &report);
    else hr = EndfieldOriginalM23DxbcValidate(device, context, &report);
    std::printf(
        "mode=%s feature_level=0x%x result=0x%08lx shaders=0x%x input=0x%x vb=0x%x "
        "vs_cb_creation=0x%x ps_cb_creation=0x%x srv_creation=0x%x "
        "sampler_creation=0x%x states=0x%x vs_bind=0x%x ps_bind=0x%x "
        "input_bind=0x%x vb_bind=0x%x vs_cb_bind=0x%x ps_cb_bind=0x%x "
        "srv_bind=0x%x sampler_bind=0x%x state_bind=0x%x vs_srv_create=0x%x "
        "vs_srv_bind=0x%x rt_bind=0x%x topology=0x%x viewport=0x%x "
        "draw=%u finite=%u changed=%u fidelity=%u readback=[%.9g,%.9g,%.9g,%.9g]\n",
        (exactTexturesHighNeutralRgbGrid || exactTexturesHighNeutralRgb) ? "diagnostic_vs_exact_ps_exact_textures_high_neutral_rgb_gate" : (exactTexturesNamedLow ? "diagnostic_vs_exact_ps_exact_textures_named_low" : (exactTexturesHighNeutral ? "diagnostic_vs_exact_ps_exact_textures_high_neutral" : (highNeutralOverride ? "diagnostic_vs_exact_ps_high_neutral_override" : (highNeutral ? "diagnostic_vs_exact_ps_high_neutral" : (highBaseline ? "diagnostic_vs_exact_ps_high_baseline" : (highProbe ? "diagnostic_vs_exact_ps_high_probe" : (namedLow ? "diagnostic_vs_exact_ps_named_low" : (diagnosticVs ? "diagnostic_vs_exact_ps" : "exact_pair")))))))),
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
            << "  \"mode\": \"" << (exactTexturesHighNeutralRgb ? "diagnostic_vs_exact_ps_exact_textures_high_neutral_rgb_gate" : (exactTexturesNamedLow ? "diagnostic_vs_exact_ps_exact_textures_named_low" : (exactTexturesHighNeutral ? "diagnostic_vs_exact_ps_exact_textures_high_neutral" : (highNeutralOverride ? "diagnostic_vs_exact_ps_high_neutral_override" : (highNeutral ? "diagnostic_vs_exact_ps_high_neutral" : (highBaseline ? "diagnostic_vs_exact_ps_high_baseline" : (highProbe ? "diagnostic_vs_exact_ps_high_probe" : (namedLow ? "diagnostic_vs_exact_ps_named_low" : (diagnosticVs ? "diagnostic_vs_exact_ps" : "exact_pair"))))))))) << "\",\n"
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
            << "  \"high_probe_execution_mask\": \"0x" << report.highProbeExecutionMask << "\",\n"
            << "  \"high_probe_register\": " << report.highProbeRegister << ",\n"
            << "  \"high_probe_component\": " << report.highProbeComponent << ",\n"
            << "  \"high_baseline_value_mask\": \"0x" << report.highBaselineValueMask << "\",\n"
            << "  \"high_ablation_group_mask\": " << report.highAblationGroupMask << ",\n"
            << "  \"high_neutral_domain_mask\": \"0x" << report.highNeutralDomainMask << "\",\n"
            << "  \"diagnostic_b2_gate_mask\": \"0x" << report.diagnosticB2GateMask << "\",\n"
            << "  \"high_neutral_override_mask\": \"0x" << report.highNeutralOverrideMask << "\",\n"
            << "  \"synthetic_t0_readback_mask\": \"0x" << report.syntheticT0ReadbackMask << "\",\n"
            << "  \"synthetic_t0_hash_mask\": \"0x" << report.syntheticT0HashMask << "\",\n"
            << "  \"synthetic_t0_sha256\": \"" << report.syntheticT0Sha256 << "\",\n"
            << "  \"exact_texture_source_hash_mask\": \"0x" << std::hex << report.exactTextureSourceHashMask << std::dec << "\",\n"
            << "  \"exact_texture_decode_mask\": \"0x" << std::hex << report.exactTextureDecodeMask << std::dec << "\",\n"
            << "  \"exact_texture_widths\": [" << report.exactTextureWidth[0] << "," << report.exactTextureWidth[1] << "," << report.exactTextureWidth[2] << "," << report.exactTextureWidth[3] << "," << report.exactTextureWidth[4] << "],\n"
            << "  \"exact_texture_heights\": [" << report.exactTextureHeight[0] << "," << report.exactTextureHeight[1] << "," << report.exactTextureHeight[2] << "," << report.exactTextureHeight[3] << "," << report.exactTextureHeight[4] << "],\n"
            << "  \"exact_texture_vs_signature_mask\": \"0x" << report.exactTextureVsSignatureMask << "\",\n"
            << "  \"exact_texture_vs_source_hash_mask\": \"0x" << report.exactTextureVsSourceHashMask << "\",\n"
            << "  \"exact_texture_vs_compiled_hash_mask\": \"0x" << report.exactTextureVsCompiledHashMask << "\",\n"
            << "  \"exact_texture_vs_source_sha256\": \"" << report.exactTextureVsSourceSha256 << "\",\n"
            << "  \"exact_texture_vs_compiled_sha256\": \"" << report.exactTextureVsCompiledSha256 << "\",\n"
            << "  \"exact_texture_grid_size\": " << report.exactTextureGridSize << ",\n"
            << "  \"exact_texture_grid_finite_pixels\": " << report.exactTextureGridFinitePixels << ",\n"
            << "  \"exact_texture_grid_nonzero_pixels\": " << report.exactTextureGridNonzeroPixels << ",\n"
            << "  \"exact_texture_grid_max_rgba\": [" << report.exactTextureGridMax[0] << "," << report.exactTextureGridMax[1] << "," << report.exactTextureGridMax[2] << "," << report.exactTextureGridMax[3] << "],\n"
            << "  \"exact_texture_causal_override_mask\": \"0x" << report.exactTextureCausalOverrideMask << "\",\n"
            << "  \"exact_texture_grid_rgb_nonzero_pixels\": " << report.exactTextureGridRgbNonzeroPixels << ",\n"
            << "  \"exact_texture_grid_alpha_nonzero_pixels\": " << report.exactTextureGridAlphaNonzeroPixels << ",\n"
            << "  \"exact_texture_grid_rgb_max\": [" << report.exactTextureGridRgbMax[0] << "," << report.exactTextureGridRgbMax[1] << "," << report.exactTextureGridRgbMax[2] << "],\n"
            << "  \"exact_texture_grid_rgb_min\": [" << report.exactTextureGridRgbMin[0] << "," << report.exactTextureGridRgbMin[1] << "," << report.exactTextureGridRgbMin[2] << "],\n"
            << "  \"exact_texture_color_space_assumption\": \"WIC 32bpp RGBA uploaded as UNORM; no sRGB transform\",\n"
            << "  \"visual_fidelity_claim\": " << report.visualFidelityClaim << ",\n"
            << "  \"b4_high_semantics\": \"zero_or_sentinel_only_non_fidelity\",\n"
            << "  \"readback\": [" << report.readback[0] << "," << report.readback[1] << "," << report.readback[2] << "," << report.readback[3] << "]\n}\n";
    }

    if (context != nullptr) context->Release();
    if (device != nullptr) device->Release();
    CoUninitialize();
    bool visualGridComplete = !exactTexturesHighNeutralRgbGrid;
    if (exactTexturesHighNeutralRgbGrid) {
        visualGridComplete = true;
        std::uint32_t visualGridNonzero = 0;
        for (float value : visualGrid) {
            if (!std::isfinite(value)) {
                visualGridComplete = false;
                break;
            }
        }
        for (std::uint32_t pixel = 0; pixel < 16u * 16u; ++pixel) {
            const float* value = visualGrid + pixel * 4u;
            if (value[0] != 0.0f || value[1] != 0.0f ||
                value[2] != 0.0f || value[3] != 0.0f)
                ++visualGridNonzero;
        }
        // The aggregate count from RunValidation must agree with the copied
        // payload. This catches an ignored/truncated output pointer while
        // allowing legitimate zero-valued edge texels.
        visualGridComplete = visualGridComplete &&
            visualGridNonzero == report.exactTextureGridNonzeroPixels;
    }
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
    const bool complete = common && (exactTexturesNamedLow || exactTexturesHighNeutral || exactTexturesHighNeutralRgb || exactTexturesHighNeutralRgbGrid
        ? (report.inputLayoutMask == 0u && report.vertexBufferMask == 0u &&
           report.vertexShaderResourceCreationMask == 0u && report.vertexShaderResourceBindingMask == 0u &&
           report.exactTextureSourceHashMask == 0x1fu && report.exactTextureDecodeMask == 0x1fu &&
           report.exactTextureVsSignatureMask == 1u && report.exactTextureVsSourceHashMask == 1u &&
           report.exactTextureVsCompiledHashMask == 1u && report.exactTextureGridSize == 16u &&
           report.exactTextureGridFinitePixels == 256u &&
           ((!exactTexturesHighNeutralRgb && !exactTexturesHighNeutralRgbGrid) || report.exactTextureCausalOverrideMask == 1u) &&
           visualGridComplete)
        : highNeutralOverride
        ? (report.inputLayoutMask == 0u && report.vertexBufferMask == 0u &&
           report.vertexShaderResourceCreationMask == 0u && report.vertexShaderResourceBindingMask == 0u &&
           report.diagnosticVsSignatureMask == 1u && report.diagnosticVsSourceHashMask == 1u &&
           report.diagnosticVsCompiledHashMask == 1u && report.highNeutralDomainMask == 1u &&
           report.highNeutralOverrideMask != 0u && report.diagnosticB2GateMask == 1u)
        : highNeutral
        ? (report.inputLayoutMask == 0u && report.vertexBufferMask == 0u &&
           report.vertexShaderResourceCreationMask == 0u && report.vertexShaderResourceBindingMask == 0u &&
           report.diagnosticVsSignatureMask == 1u && report.diagnosticVsSourceHashMask == 1u &&
           report.diagnosticVsCompiledHashMask == 1u && report.highNeutralDomainMask == 1u &&
           report.diagnosticB2GateMask == 1u)
        : namedLow
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
