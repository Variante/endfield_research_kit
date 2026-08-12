#!/usr/bin/env python3
"""Validate the project-local exact-DXBC diagnostic and live reports."""

from __future__ import annotations

import hashlib
import json
import re
import struct
from pathlib import Path


TOOL = Path(__file__).resolve().parent
PROJECT = TOOL.parents[1]
REPO = PROJECT.parent
ASSET_ROOT = PROJECT / "Assets/EndfieldGraphShaderLab"
PLUGIN = ASSET_ROOT / "Plugins/x86_64/OriginalDxbcSwapPlugin.dll"
PLUGIN_META = Path(str(PLUGIN) + ".meta")
SHADER = (
    ASSET_ROOT
    / "Shaders/Diagnostics/EndfieldOriginalDxbcResolverDiagnostic.shader"
)
RUNTIME = (
    ASSET_ROOT
    / "Runtime/Diagnostics/EndfieldOriginalDxbcDiagnosticRuntime.cs"
)
BUILDER = (
    ASSET_ROOT
    / "Editor/Scratch/EndfieldOriginalDxbcDiagnosticBuilder.cs"
)
LIVE_ROOT = (
    PROJECT
    / "scratch/reverse_engineering/original_dxbc_exact_diagnostic"
)
DURABLE = (
    REPO
    / "scratch/reverse_engineering/gacha_unity_original_bytecode_execution"
    / "unity_live_validation.json"
)

VERTEX_HASH = "a6afe2c96caa3fd940004ce9ee725886d0f8df683d5f73403278743e32563155"
PIXEL_HASH = "b21a1e35eda1c5bcb60198c6af313799ddcc94d0cee0be9025938f3ba8c56b6f"
PLUGIN_HASH = "fc5cdd483240ddc2588918749680bced61e49a83d53b5e34c208ab1b3f71fa6c"
VALIDATOR_HASH = "3cc382f0fe0307051a5d9f53de50a9750406761ef5fc7ab56b89581f376fd9fd"
KEYWORD = "ENDFIELD_ORIGINAL_DXBC_EXACT"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class PE:
    def __init__(self, data: bytes):
        self.data = data
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe : pe + 4] != b"PE\0\0":
            raise ValueError("not a PE image")
        count = struct.unpack_from("<H", data, pe + 6)[0]
        optional_size = struct.unpack_from("<H", data, pe + 20)[0]
        self.optional = pe + 24
        if struct.unpack_from("<H", data, self.optional)[0] != 0x20B:
            raise ValueError("not PE32+")
        table = self.optional + optional_size
        self.sections = []
        for index in range(count):
            off = table + index * 40
            virtual_size, rva, raw_size, raw = struct.unpack_from(
                "<IIII", data, off + 8
            )
            self.sections.append((rva, max(virtual_size, raw_size), raw))

    def offset(self, rva: int) -> int:
        for start, size, raw in self.sections:
            if start <= rva < start + size:
                return raw + rva - start
        raise ValueError(f"unmapped RVA 0x{rva:x}")

    def exports(self) -> list[str]:
        export_rva, export_size = struct.unpack_from(
            "<II", self.data, self.optional + 112
        )
        if not export_rva or not export_size:
            return []
        off = self.offset(export_rva)
        values = struct.unpack_from("<IIHHIIIIIII", self.data, off)
        name_count = values[7]
        names_rva = values[9]
        names_off = self.offset(names_rva)
        result = []
        for index in range(name_count):
            name_rva = struct.unpack_from("<I", self.data, names_off + index * 4)[0]
            name_off = self.offset(name_rva)
            end = self.data.index(b"\0", name_off)
            result.append(self.data[name_off:end].decode("ascii"))
        return sorted(result)


def load_live(
    path: Path,
    host: str,
    errors: list[str],
    allow_no_activation: bool = False,
) -> dict:
    if not path.is_file():
        errors.append(f"missing {host} report: {path}")
        return {"host": host, "status": "missing"}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid {host} report: {exc}")
        return {"host": host, "status": "invalid"}
    expected = {
        "graphics_device_type": "Direct3D11",
        "keyword": KEYWORD,
        "vertex_sha256": VERTEX_HASH,
        "pixel_sha256": PIXEL_HASH,
        "native_contract_version": 1,
        "production_room_submitted": False,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            errors.append(
                f"{host} report {key}={report.get(key)!r}, expected {value!r}"
            )
    status = report.get("status")
    if status == "pass":
        passing = {
            "unarmed_callback_count": 0,
            "blocked_callback_count": 0,
            "failure_count": 0,
            "last_hresult": "0x00000000",
            "render_event_count": 2,
            "post_draw_exact_shader_objects_bound": True,
            "shader_resource_mask": "0x3fffffe",
            "resource_binding_compatible": True,
            "readback_changed_from_sentinel": True,
        }
        for key, value in passing.items():
            if report.get(key) != value:
                errors.append(
                    f"{host} report {key}={report.get(key)!r}, "
                    f"expected {value!r}"
                )
        callback_count = report.get("callback_count")
        vertex_swap_count = report.get("vertex_swap_count")
        pixel_swap_count = report.get("pixel_swap_count")
        if not all(
            isinstance(value, int)
            for value in (callback_count, vertex_swap_count, pixel_swap_count)
        ):
            errors.append(
                f"{host} compiler counters are not integers: "
                f"callbacks={callback_count!r}, vertex={vertex_swap_count!r}, "
                f"pixel={pixel_swap_count!r}"
            )
        elif callback_count == 0:
            if vertex_swap_count != 0 or pixel_swap_count != 0:
                errors.append(
                    f"{host} compiler counters are inconsistent for direct runtime "
                    f"mode: callbacks=0, vertex={vertex_swap_count}, "
                    f"pixel={pixel_swap_count}"
                )
        elif callback_count < 2 or vertex_swap_count < 1 or pixel_swap_count < 1:
            errors.append(
                f"{host} compiler counters are incomplete: callbacks={callback_count}, "
                f"vertex={vertex_swap_count}, pixel={pixel_swap_count}"
            )
    elif not (allow_no_activation and status == "no_activation"):
        errors.append(f"{host} report status={status!r}, expected 'pass'")
    if not isinstance(report.get("plugin_load_count"), int) or report.get(
        "plugin_load_count", 0
    ) < 1:
        errors.append(f"{host} report has no native plugin load")
    if not isinstance(report.get("configure_event_count"), int) or report.get(
        "configure_event_count", 0
    ) < 1:
        errors.append(f"{host} report has no shader-extension configure event")
    return report


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    files = {}
    paths = {
        "vertex_dxbc": TOOL / "bytecode/selected_deferred_resolver_vs.dxbc",
        "pixel_dxbc": TOOL / "bytecode/selected_deferred_resolver_ps.dxbc",
        "native_source": TOOL / "OriginalDxbcSwapPlugin.cpp",
        "generator": TOOL / "generate_embedded_header.py",
        "build_helper": TOOL / "build_plugin.ps1",
        "tool_readme": TOOL / "README.md",
        "provenance": TOOL / "provenance.json",
        "generated_header": TOOL / "build/EmbeddedDxbc.generated.h",
        "warp_validator": TOOL / "build/ValidateEmbeddedDxbc.exe",
        "plugin": PLUGIN,
        "plugin_meta": PLUGIN_META,
        "shader": SHADER,
        "runtime": RUNTIME,
        "builder": BUILDER,
    }
    blobs: dict[str, bytes] = {}
    for name, path in paths.items():
        if not path.is_file():
            errors.append(f"missing project artifact: {path}")
            continue
        data = path.read_bytes()
        blobs[name] = data
        files[name] = {
            "path": str(path.relative_to(REPO)).replace("\\", "/"),
            "size": len(data),
            "sha256": sha256(data),
        }

    if "vertex_dxbc" in blobs:
        check(sha256(blobs["vertex_dxbc"]) == VERTEX_HASH, "vertex DXBC drift", errors)
        check(len(blobs["vertex_dxbc"]) == 496, "vertex DXBC size drift", errors)
    if "pixel_dxbc" in blobs:
        check(sha256(blobs["pixel_dxbc"]) == PIXEL_HASH, "pixel DXBC drift", errors)
        check(len(blobs["pixel_dxbc"]) == 48_984, "pixel DXBC size drift", errors)
    if "plugin" in blobs:
        check(sha256(blobs["plugin"]) == PLUGIN_HASH, "plugin binary drift", errors)
        check(
            blobs["plugin"].count(blobs.get("vertex_dxbc", b"missing")) == 1,
            "plugin does not contain exactly one selected VS blob",
            errors,
        )
        check(
            blobs["plugin"].count(blobs.get("pixel_dxbc", b"missing")) == 1,
            "plugin does not contain exactly one selected PS blob",
            errors,
        )
        expected_exports = [
            "EndfieldOriginalDxbcGetBlockedCount",
            "EndfieldOriginalDxbcGetCallbackCount",
            "EndfieldOriginalDxbcGetConfigureCount",
            "EndfieldOriginalDxbcGetConstantBufferMask",
            "EndfieldOriginalDxbcGetContractVersion",
            "EndfieldOriginalDxbcGetDiagnosticArmed",
            "EndfieldOriginalDxbcGetExactShaderBound",
            "EndfieldOriginalDxbcGetFailureCount",
            "EndfieldOriginalDxbcGetLastResult",
            "EndfieldOriginalDxbcGetPixelSwapCount",
            "EndfieldOriginalDxbcGetPluginLoadCount",
            "EndfieldOriginalDxbcGetPostDrawShaderResourceMask",
            "EndfieldOriginalDxbcGetRenderEventCount",
            "EndfieldOriginalDxbcGetRenderEventFunc",
            "EndfieldOriginalDxbcGetSamplerMask",
            "EndfieldOriginalDxbcGetShaderResourceMask",
            "EndfieldOriginalDxbcGetUnarmedCallbackCount",
            "EndfieldOriginalDxbcGetVertexSwapCount",
            "EndfieldOriginalDxbcSetDiagnosticArmed",
            "EndfieldOriginalDxbcSetDiagnosticTexturePointers",
            "UnityPluginLoad",
            "UnityPluginUnload",
            "UnityShaderCompilerExtEvent",
        ]
        try:
            check(
                PE(blobs["plugin"]).exports() == expected_exports,
                "plugin export contract drift",
                errors,
            )
        except Exception as exc:
            errors.append(f"plugin PE parse failed: {exc}")
    if "warp_validator" in blobs:
        check(
            sha256(blobs["warp_validator"]) == VALIDATOR_HASH,
            "WARP validator drift",
            errors,
        )

    native = blobs.get("native_source", b"").decode("utf-8", "replace")
    shader = blobs.get("shader", b"").decode("utf-8", "replace")
    runtime = blobs.get("runtime", b"").decode("utf-8", "replace")
    builder = blobs.get("builder", b"").decode("utf-8", "replace")
    meta = blobs.get("plugin_meta", b"").decode("utf-8", "replace")
    for token in [
        KEYWORD,
        "kUnityShaderCompilerExtCompPlatformD3D11",
        "EndfieldOriginalDxbcSetDiagnosticArmed",
        "g_vertexClaimed",
        "g_pixelClaimed",
        "CreateVertexShader",
        "CreatePixelShader",
        "CreateShaderResourceView",
        "EndfieldOriginalDxbcSetDiagnosticTexturePointers",
        "PSGetConstantBuffers",
        "PSGetShaderResources",
        "PSGetSamplers",
    ]:
        check(token in native, f"native guard token missing: {token}", errors)
    for token in [
        "#pragma only_renderers d3d11",
        f"#pragma multi_compile_local __ {KEYWORD}",
        "EndfieldCB8 : register(b8)",
        "_EndfieldTextureT25 : register(t25)",
        "sampler_EndfieldTextureT6 : register(s4)",
    ]:
        check(token in shader, f"shader contract token missing: {token}", errors)
    for token in [
        "Application.isBatchMode",
        "GraphicsDeviceType.Direct3D11",
        "callback_count",
        "production_room_submitted",
        "SetGlobalConstantBuffer",
        "IssuePluginEvent",
        "ReadPixels",
        "logical GBuffer in backend order t23=C, t24=B, t25=A",
        "else if (slot == 23)",
        "texture = gbufferC",
        "else if (slot == 25)",
        "texture = gbufferA",
    ]:
        check(token in runtime, f"runtime fail-closed token missing: {token}", errors)
    for token in [
        "SetCompatibleWithAnyPlatform(false)",
        "SetCompatibleWithEditor(true)",
        "StandaloneWindows64",
        "GraphicsDeviceType.Direct3D11",
        "OriginalDxbcExactDiagnostic.unity",
    ]:
        check(token in builder, f"builder platform token missing: {token}", errors)
    check(
        re.search(
            r"- first:\s+Any:\s+second:\s+enabled: 0",
            meta,
            re.MULTILINE,
        )
        is not None,
        "plugin importer Any-platform disable is missing",
        errors,
    )
    check(
        re.search(
            r"- first:\s+Editor: Editor\s+second:\s+enabled: 1"
            r"[\s\S]*?CPU: x86_64[\s\S]*?OS: Windows",
            meta,
            re.MULTILINE,
        )
        is not None,
        "plugin importer Windows x86_64 Editor filter is missing",
        errors,
    )
    check(
        re.search(
            r"- first:\s+Standalone: Win64\s+second:\s+enabled: 1"
            r"[\s\S]*?CPU: x86_64",
            meta,
            re.MULTILINE,
        )
        is not None,
        "plugin importer Win64 filter is missing",
        errors,
    )
    check("Direct3D12" not in native, "native source mentions Direct3D12", errors)
    check("only_renderers d3d11" in shader, "shader is not D3D11-only", errors)

    editor = load_live(
        LIVE_ROOT / "editor_validation.json",
        "editor",
        errors,
        allow_no_activation=True,
    )
    standalone = load_live(
        LIVE_ROOT / "standalone_validation.json", "standalone", errors
    )
    build_report_path = LIVE_ROOT / "standalone_build.json"
    build_report = {}
    if build_report_path.is_file():
        try:
            build_report = json.loads(build_report_path.read_text(encoding="utf-8"))
            check(
                build_report.get("graphics_apis") == ["Direct3D11"],
                "standalone build is not explicitly D3D11-only",
                errors,
            )
            check(
                build_report.get("status") == "pass",
                "standalone build report did not pass",
                errors,
            )
        except Exception as exc:
            errors.append(f"invalid standalone build report: {exc}")
    else:
        errors.append(f"missing standalone build report: {build_report_path}")

    verdict = "ACTIVATION" if not errors else "NO_ACTIVATION"
    if verdict == "ACTIVATION":
        activation_scope = (
            "editor_and_standalone_d3d11_isolated_diagnostic"
            if editor.get("status") == "pass"
            else "standalone_d3d11_isolated_diagnostic"
        )
    else:
        activation_scope = "installed_default_off"
    report = {
        "schema": "endfield.original-dxbc-exact-live-validation.v1",
        "verdict": verdict,
        "activation_scope": activation_scope,
        "production_room_draw_enabled": False,
        "retail_process_launched": False,
        "graphics_api": "Direct3D11",
        "keyword": KEYWORD,
        "vertex_sha256": VERTEX_HASH,
        "pixel_sha256": PIXEL_HASH,
        "plugin_sha256": files.get("plugin", {}).get("sha256", ""),
        "validator_sha256": files.get("warp_validator", {}).get("sha256", ""),
        "editor_validation": editor,
        "standalone_validation": standalone,
        "standalone_build": build_report,
        "project_files": files,
        "errors": errors,
    }
    DURABLE.parent.mkdir(parents=True, exist_ok=True)
    DURABLE.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{verdict}: {DURABLE}")
    for error in errors:
        print(f"ERROR: {error}")
    return 0 if verdict == "ACTIVATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
