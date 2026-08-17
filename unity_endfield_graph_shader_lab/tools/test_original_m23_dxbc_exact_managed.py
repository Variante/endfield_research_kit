"""Focused contract checks for the isolated M23 managed bridge path."""
import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "Assets" / "EndfieldGraphShaderLab"
RUNTIME = ASSETS / "Runtime" / "Diagnostics" / "EndfieldOriginalM23DxbcDiagnosticRuntime.cs"
BUILDER = ASSETS / "Editor" / "Scratch" / "EndfieldOriginalM23DxbcDiagnosticBuilder.cs"
SHADER = ASSETS / "Shaders" / "Diagnostics" / "EndfieldOriginalM23DxbcDiagnostic.shader"
NATIVE = ROOT / "tools" / "original_m23_dxbc_exact" / "OriginalM23DxbcUnityBridge.cpp"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check_source_contract():
    runtime = RUNTIME.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    shader = SHADER.read_text(encoding="utf-8")
    native = NATIVE.read_text(encoding="utf-8")
    require(RUNTIME.with_suffix(".cs.meta").exists(), "runtime .meta is missing")
    require(BUILDER.with_suffix(".cs.meta").exists(), "builder .meta is missing")
    require(SHADER.with_suffix(".shader.meta").exists(), "shader .meta is missing")
    for text, token, label in (
        (runtime, "-endfield-original-m23-dxbc-diagnostic", "runtime token"),
        (runtime, "-endfield-original-m23-dxbc-visual-grid", "visual-grid token"),
        (builder, "EndfieldOriginalM23DxbcDiagnosticRuntime.ActivationArgument", "builder token"),
        (shader, "ENDFIELD_ORIGINAL_M23_DXBC_EXACT", "shader keyword"),
    ):
        require(token in text, label + " is absent")
    require("Application.isBatchMode" in runtime and "GraphicsDeviceType.Direct3D11" in runtime,
            "runtime lacks batch/D3D11 gates")
    require("Application.isBatchMode" in builder and "GraphicsDeviceType.Direct3D11" in builder,
            "builder lacks batch/D3D11 gates")
    require('"visual_fidelity_claim\\": false' in runtime.replace("'", '"') or
            '"visual_fidelity_claim": false' in runtime,
            "runtime does not distinguish execution from fidelity")
    require('"synthetic_grid\\": ' in runtime.replace("'", '"') and
            '"actor_particle_input\\": false' in runtime.replace("'", '"'),
            "runtime does not expose the synthetic/actor input boundary")
    require("CopyVisualGrid(values, VisualGridFloatCount)" in runtime,
            "runtime does not copy the complete visual grid")
    require("eventFunction, 3" in runtime, "managed cleanup event 3 is not queued")
    require("GetShellInputObservedCount" in runtime and "GetInputMismatchCount" not in runtime,
            "managed ABI still uses the removed input-mismatch export")
    require("GetCleanupCount" in runtime and "GetCleanupPending" in runtime,
            "managed cleanup ABI is incomplete")
    for export in (
        "EndfieldOriginalM23DxbcBridgeSetVisualMode",
        "EndfieldOriginalM23DxbcBridgeGetVisualMode",
        "EndfieldOriginalM23DxbcBridgeGetVisualGridValid",
        "EndfieldOriginalM23DxbcBridgeGetVisualConfigMask",
        "EndfieldOriginalM23DxbcBridgeGetVisualGridSize",
        "EndfieldOriginalM23DxbcBridgeGetVisualGridFinitePixels",
        "EndfieldOriginalM23DxbcBridgeGetVisualGridNonzeroPixels",
        "EndfieldOriginalM23DxbcBridgeGetVisualGridRgbNonzeroPixels",
        "EndfieldOriginalM23DxbcBridgeGetVisualGridAlphaNonzeroPixels",
        "EndfieldOriginalM23DxbcBridgeCopyVisualGrid",
    ):
        require(export in runtime, "managed visual-grid ABI is missing " + export)
    expected = re.findall(r"EndfieldOriginalM23DxbcBridge[A-Za-z0-9_]+", runtime)
    native_exports = set(re.findall(r"EndfieldOriginalM23DxbcBridge[A-Za-z0-9_]+(?=\s*\()", native))
    missing = sorted(set(expected) - native_exports)
    require(not missing, "managed ABI exports missing from native source: " + ", ".join(missing))
    require("OriginalM23DxbcExactDiagnostic" in builder and "BuildPipeline.BuildPlayer" in builder,
            "builder does not produce isolated diagnostic player")
    for token in (
        "CaptureRealDrawState(eventId == 5)",
        "EndfieldOriginalM23DxbcBridgeGetRealDrawBeforeBindingMask",
        "EndfieldOriginalM23DxbcBridgeGetRealDrawAfterVertexStrideAt",
        "EndfieldOriginalM23DxbcBridgeGetRealDrawAfterIndexFormat",
        "EndfieldOriginalM23DxbcBridgeGetRealDrawObserverDidNotClearState",
    ):
        require(token in native, "native real-draw observer contract is missing " + token)
    require("eventId == 4 || eventId == 5" in native and
            "observerDidNotClearState" in native,
            "native real-draw observer lacks its non-destructive event boundary")
    require("GetRealDrawObservationNoStateClear" not in native,
            "native observer still exposes the misleading no-state-clear claim")
    require("EndfieldM23CB0" in shader and "register(b4)" in shader and
            "register(t4)" in shader and "register(s4)" in shader,
            "shader shell does not expose M23 five-slot ABI")


def check_report(path, require_pass=False, require_visual_grid=False):
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    require(report.get("schema") == "endfield.original-m23-dxbc-exact-live.v1",
            "unexpected managed report schema")
    require(report.get("visual_fidelity_claim") is False,
            "managed report made a visual-fidelity claim")
    require(report.get("actor_particle_input") is False,
            "managed report did not identify actor-particle input boundary")
    if require_visual_grid:
        require(report.get("status") == "pass", "visual-grid diagnostic did not pass")
        require(report.get("synthetic_grid") is True,
                "visual-grid report is not marked synthetic")
        require(report.get("visual_fidelity_claim") is False,
                "visual-grid report made a visual-fidelity claim")
        require(report.get("visual_grid_mode") == 1,
                "visual-grid mode was not selected")
        require(report.get("visual_grid_valid") is True,
                "visual-grid native validity gate did not pass")
        require(report.get("visual_grid_config_mask") == 0x7F,
                "unexpected visual-grid config mask")
        require(report.get("visual_grid_size") == 16 and
                report.get("visual_grid_float_count") == 1024,
                "unexpected visual-grid dimensions")
        require(report.get("visual_grid_finite_pixels") == 256,
                "visual-grid finite-pixel gate did not pass")
        require(re.fullmatch(r"[0-9a-f]{64}", report.get("visual_grid_float_sha256", "")),
                "visual-grid float hash is missing")
        png = report.get("visual_grid_png")
        if png:
            require(Path(png).exists(), "visual-grid PNG path does not exist")
    if require_pass:
        require(report.get("status") == "pass", "M23 native execution gate did not pass")
        require(report.get("execution_binding_compatible") is True,
                "M23 execution gate is not binding-compatible")
        require(report.get("cleanup_count") == 1 and report.get("cleanup_pending") == 0,
                "M23 native cleanup was not completed")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--report")
    parser.add_argument("--d3d12-report")
    parser.add_argument("--visual-grid", action="store_true")
    args = parser.parse_args(argv)
    check_source_contract()
    if args.report:
        check_report(args.report, require_pass=True, require_visual_grid=args.visual_grid)
    if args.d3d12_report:
        report = json.loads(Path(args.d3d12_report).read_text(encoding="utf-8"))
        require(report.get("schema") == "endfield.original-m23-dxbc-d3d12-non-activation.v1",
                "unexpected D3D12 non-activation schema")
        require(report.get("visual_fidelity_claim") is False,
                "D3D12 report made a visual-fidelity claim")
    print("M23 managed bridge contract: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, json.JSONDecodeError) as error:
        print("M23 managed bridge contract: FAIL: " + str(error), file=sys.stderr)
        raise SystemExit(1)
