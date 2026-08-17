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
    require("eventFunction, 3" in runtime, "managed cleanup event 3 is not queued")
    require("GetShellInputObservedCount" in runtime and "GetInputMismatchCount" not in runtime,
            "managed ABI still uses the removed input-mismatch export")
    require("GetCleanupCount" in runtime and "GetCleanupPending" in runtime,
            "managed cleanup ABI is incomplete")
    expected = re.findall(r"EndfieldOriginalM23DxbcBridge[A-Za-z0-9_]+", runtime)
    native_exports = set(re.findall(r"EndfieldOriginalM23DxbcBridge[A-Za-z0-9_]+(?=\s*\()", native))
    missing = sorted(set(expected) - native_exports)
    require(not missing, "managed ABI exports missing from native source: " + ", ".join(missing))
    require("OriginalM23DxbcExactDiagnostic" in builder and "BuildPipeline.BuildPlayer" in builder,
            "builder does not produce isolated diagnostic player")
    require("EndfieldM23CB0" in shader and "register(b4)" in shader and
            "register(t4)" in shader and "register(s4)" in shader,
            "shader shell does not expose M23 five-slot ABI")


def check_report(path, require_pass=False):
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    require(report.get("schema") == "endfield.original-m23-dxbc-exact-live.v1",
            "unexpected managed report schema")
    require(report.get("visual_fidelity_claim") is False,
            "managed report made a visual-fidelity claim")
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
    args = parser.parse_args(argv)
    check_source_contract()
    if args.report:
        check_report(args.report, require_pass=True)
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
