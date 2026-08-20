#!/usr/bin/env python3
"""Pin the BurstDirectCall initialisation and resolution boundary.

The three range-kernel rows requested by the character-recovery work are
managed BurstDirectCall wrappers, not the generated Burst implementation.  A
wrapper's body can prove the guarded ``GetFunctionPointer`` path, the managed
fallback, and the BurstCompiler/CompilerService hand-off.  It cannot, in this
client, prove which 32-hex export in ``lib_burst_generated.dll`` is eventually
selected: the final name is passed through a late-bound native service.

This contract therefore records exact metadata identities, registration
addresses, bounded method spans/hashes, selected direct calls, RIP-relative
globals, and the bounded export-directory candidate set.  It intentionally
does not invent a wrapper-to-export mapping.  Runtime GetProcAddress telemetry
is the remaining evidence required to close that boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import struct
import sys
from bisect import bisect_right
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_burst_wrapper_contract.json"
DEFAULT_MARKDOWN = SOURCE_ROOT / "secondary_dynamics_burst_wrapper_contract.md"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_LIB_BURST_SHA256 = "ee8702dd63dec2db7dc29d5bc23b8acd032f0e19a0daad5f69e6c45f9d3ceb99"
EXPECTED_CODE_REGISTRATION = 0x18B9217D0
EXPECTED_METADATA_REGISTRATION = 0x18B921C30

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    """Raised when the pinned native evidence no longer matches."""


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load IL2CPP helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _helpers() -> tuple[Any, Any]:
    root = REPO_ROOT / "tools/endfield-il2cpp"
    return (
        _load("secondary_burst_metadata", root / "catalog_option_flow_metadata.py"),
        _load("secondary_burst_native", root / "map_body_targets_to_gameassembly.py"),
    )


def _hex(value: int) -> str:
    return f"0x{value:x}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _file(path: Path, digest: str | None = None) -> dict[str, Any]:
    return {"path": _path(path), "size": path.stat().st_size, "sha256": digest or _sha256(path)}


def _native_indexes(metadata: Path, gameassembly: Path) -> tuple[Any, Any, Any, dict[int, list[dict[str, Any]]], list[int], int]:
    catalog, native = _helpers()
    md = catalog.Metadata(metadata)
    pe = native.PeImage(gameassembly)
    image_names = {md.string(image.name_index) for image in md.images}
    code_registration = native.find_code_registration(pe, image_names)
    if code_registration != EXPECTED_CODE_REGISTRATION:
        raise ContractError(
            f"code registration drift: {_hex(code_registration)} != {_hex(EXPECTED_CODE_REGISTRATION)}"
        )
    metadata_registration = native.find_metadata_registration(pe, code_registration)
    if metadata_registration != EXPECTED_METADATA_REGISTRATION:
        raise ContractError(
            f"metadata registration drift: {_hex(metadata_registration)} != {_hex(EXPECTED_METADATA_REGISTRATION)}"
        )
    modules = native.parse_codegen_modules(pe, code_registration)
    ranges = native.image_method_ranges(md)
    _pointers_by_image, method_by_pointer = native.build_pointer_indexes(pe, md, modules, ranges)
    all_pointers = sorted(pointer for pointer in method_by_pointer if pointer)
    return native, md, pe, method_by_pointer, all_pointers, metadata_registration


def _register_method_rows(method_by_pointer: dict[int, list[dict[str, Any]]], method_index: int) -> list[tuple[int, dict[str, Any]]]:
    return [
        (pointer, signature)
        for pointer, signatures in method_by_pointer.items()
        for signature in signatures
        if int(signature.get("methodIndex", -1)) == method_index
    ]


def _method_label_matches(md: Any, method_index: int, type_name: str, method_name: str) -> bool:
    method = md.methods[method_index]
    actual_type = md.type_full_name(md.types[method.declaring_type])
    return md.string(method.name_index) == method_name and actual_type == type_name


# These are only the methods needed to close the wrapper-to-BurstCompiler
# chain.  Every row is checked against metadata and the code-registration
# pointer index before it is published.
TARGET_SPECS: dict[int, dict[str, Any]] = {
    385570: {"type": "BeyondDynamicBone.SimulationManager+StartSimulationStepJobKernels+StartSimulationStepRangeKernel_00000408$BurstDirectCall", "method": "Invoke", "role": "simulation_start_entry", "va": 0x1867775FC, "end": 0x1867779AC, "sha": "cafeebc9f217a60a011aaac5d3df41e50b0c1afe05e1189c3295a53741482530", "calls": {0x3A: (0x180035ED0, None, "runtime_class_init"), 0x46: (0x180035ED0, None, "runtime_class_init"), 0x59: (0x1800036A0, None, "delegate_field_load"), 0x60: (0x18307B8D0, 489283, "BurstCompiler.get_IsEnabled"), 0x74: (0x1800036A0, None, "delegate_field_load"), 0x7B: (0x1867775A8, 385566, "GetFunctionPointer"), 0x38B: (0x1867673DC, 385547, "managed_fallback")}, "indirect": [(0x208, "rdx", "burst_function_pointer_call")], "rip": [(0x0A, 7, "initialization_guard"), (0x33, 7, "initialization_state"), (0x3F, 7, "delegate_state"), (0x4B, 7, "initialization_guard_store"), (0x52, 7, "initialization_state_load"), (0x6D, 7, "delegate_state_load")]},
    385394: {"type": "BeyondDynamicBone.ColliderManager+StartSimulationStepJobKernels", "method": "StartSimulationStepRangeKernel", "role": "collider_start_entry", "va": 0x186761454, "end": 0x186761580, "sha": "8288afcbf74538804fca27116411829f357da2926614202c0ed6ae3313b1b9c7", "calls": {0x33: (0x180035ED0, None, "runtime_class_init"), 0x46: (0x1800036A0, None, "delegate_field_load"), 0x10C: (0x186762CC0, 385416, "BurstDirectCall.Invoke")}, "rip": [(0x17, 7, "initialization_guard"), (0x2C, 7, "initialization_state"), (0x38, 7, "initialization_guard_store"), (0x3F, 7, "initialization_state_load")]},
    385295: {"type": "BeyondDynamicBone.EndSimulationStepJobKernels", "method": "EndSimulationStepRangeKernel", "role": "collider_end_entry", "va": 0x18675A944, "end": 0x18675A9CC, "sha": "cb44336ba8aca6b48b51f77a6523c65e8bebe76b57efa5b680d4d721b28f92e1", "calls": {0x30: (0x180035ED0, None, "runtime_class_init"), 0x43: (0x1800036A0, None, "delegate_field_load"), 0x6E: (0x18675B0CC, 385317, "BurstDirectCall.Invoke")}, "rip": [(0x14, 7, "initialization_guard"), (0x29, 7, "initialization_state"), (0x35, 7, "initialization_guard_store"), (0x3C, 7, "initialization_state_load")]},
    385416: {"type": "BeyondDynamicBone.ColliderManager+StartSimulationStepJobKernels+StartSimulationStepRangeKernel_000003D8$BurstDirectCall", "method": "Invoke", "role": "collider_start_directcall", "va": 0x186762CC0, "end": 0x186762EDC, "sha": "7df4869600061f52675346458da081a90aa0afe2971e233d0fa388d9bc0d69e9", "calls": {0x33: (0x180035ED0, None, "runtime_class_init"), 0x3F: (0x180035ED0, None, "runtime_class_init"), 0x52: (0x1800036A0, None, "delegate_field_load"), 0x59: (0x18307B8D0, 489283, "BurstCompiler.get_IsEnabled"), 0x6D: (0x1800036A0, None, "delegate_field_load"), 0x74: (0x186762C6C, 385412, "GetFunctionPointer"), 0x1FD: (0x1867584A0, 385396, "managed_fallback")}, "indirect": [(0x13D, "r10", "burst_function_pointer_call")], "rip": [(0x17, 7, "initialization_guard"), (0x2C, 7, "initialization_state"), (0x38, 7, "delegate_state"), (0x44, 7, "initialization_guard_store"), (0x4B, 7, "initialization_state_load"), (0x66, 7, "delegate_state_load")]},
    385317: {"type": "BeyondDynamicBone.EndSimulationStepJobKernels+EndSimulationStepRangeKernel_000003BB$BurstDirectCall", "method": "Invoke", "role": "collider_end_directcall", "va": 0x18675B0CC, "end": 0x18675B1D4, "sha": "af0bc7f23f65b57b0635f634adad4b9024c7e7c2f36818f26b622a0d56f544f1", "calls": {0x39: (0x180035ED0, None, "runtime_class_init"), 0x45: (0x180035ED0, None, "runtime_class_init"), 0x58: (0x1800036A0, None, "delegate_field_load"), 0x5F: (0x18307B8D0, 489283, "BurstCompiler.get_IsEnabled"), 0x6F: (0x1800036A0, None, "delegate_field_load"), 0x76: (0x18675B078, 385313, "GetFunctionPointer"), 0xDD: (0x18675A834, 385294, "managed_fallback")}, "indirect": [(0xA6, "rax", "burst_function_pointer_call")], "rip": [(0x1D, 7, "initialization_guard"), (0x32, 7, "initialization_state"), (0x3E, 7, "delegate_state"), (0x4A, 7, "initialization_guard_store"), (0x51, 7, "initialization_state_load"), (0x68, 7, "delegate_state_load")]},
    385566: {"type": "BeyondDynamicBone.SimulationManager+StartSimulationStepJobKernels+StartSimulationStepRangeKernel_00000408$BurstDirectCall", "method": "GetFunctionPointer", "role": "simulation_get_function_pointer", "va": 0x1867775A8, "end": 0x1867775FC, "sha": "28798b9256325c7f41935a83b6fbf43e044259964873b31f3f4b32a16c82e982", "calls": {0x14: (0x180035ED0, None, "runtime_class_init"), 0x39: (0x18002C880, None, "runtime_static_guard"), 0x45: (0x1867774A4, 385565, "GetFunctionPointerDiscard")}, "rip": [(0x04, 7, "initialization_guard"), (0x0D, 7, "initialization_state"), (0x19, 7, "initialization_guard_store"), (0x20, 7, "initialization_state_load")]},
    385565: {"type": "BeyondDynamicBone.SimulationManager+StartSimulationStepJobKernels+StartSimulationStepRangeKernel_00000408$BurstDirectCall", "method": "GetFunctionPointerDiscard", "role": "simulation_get_function_pointer_discard", "va": 0x1867774A4, "end": 0x1867775A8, "sha": "853d297634b86c7a37e71e83706c54f28bdd5a11b27405958f7471b45df448dd", "calls": {0x28: (0x180035ED0, None, "runtime_class_init"), 0x34: (0x180035ED0, None, "runtime_class_init"), 0x40: (0x180035ED0, None, "runtime_class_init"), 0x4C: (0x180035ED0, None, "runtime_class_init"), 0x5F: (0x1800036A0, None, "delegate_field_load"), 0x78: (0x1800036A0, None, "delegate_field_load"), 0xA4: (0x1800036A0, None, "delegate_field_load"), 0xB5: (0x18474F6F0, 489285, "BurstCompiler.GetILPPMethodFunctionPointer2"), 0xD2: (0x1800036A0, None, "delegate_field_load")}, "rip": [(0x15, 7, "initialization_guard"), (0x21, 7, "type_state"), (0x2D, 7, "runtime_method_handle"), (0x39, 7, "delegate_type_handle"), (0x45, 7, "runtime_type_handle"), (0x51, 7, "initialization_guard_store"), (0x58, 7, "delegate_state_load"), (0x64, 7, "delegate_state_load"), (0x7D, 7, "ilpp_method_load"), (0x84, 7, "runtime_method_handle_load"), (0x8B, 7, "delegate_type_handle_load"), (0x9D, 7, "initialization_state_load"), (0xBA, 7, "initialization_state_load"), (0xCB, 7, "initialization_state_load"), (0xD7, 7, "ilpp_method_load")], "indirect": []},
    385412: {"type": "BeyondDynamicBone.ColliderManager+StartSimulationStepJobKernels+StartSimulationStepRangeKernel_000003D8$BurstDirectCall", "method": "GetFunctionPointer", "role": "collider_start_get_function_pointer", "va": 0x186762C6C, "end": 0x186762CC0, "sha": "92e3a26949411850485cd52ae1e51d3f50545134dd92fb24293435fc5d030052", "calls": {0x14: (0x180035ED0, None, "runtime_class_init"), 0x39: (0x18002C880, None, "runtime_static_guard"), 0x45: (0x186762B68, 385411, "GetFunctionPointerDiscard")}, "rip": [(0x04, 7, "initialization_guard"), (0x0D, 7, "initialization_state"), (0x19, 7, "initialization_guard_store"), (0x20, 7, "initialization_state_load")]},
    385411: {"type": "BeyondDynamicBone.ColliderManager+StartSimulationStepJobKernels+StartSimulationStepRangeKernel_000003D8$BurstDirectCall", "method": "GetFunctionPointerDiscard", "role": "collider_start_get_function_pointer_discard", "va": 0x186762B68, "end": 0x186762C6C, "sha": "e8504a97b60a08caeedf6e3e064a3a1bfd1916a55c65e02c3928e51cae58d1dd", "calls": {0x28: (0x180035ED0, None, "runtime_class_init"), 0x34: (0x180035ED0, None, "runtime_class_init"), 0x40: (0x180035ED0, None, "runtime_class_init"), 0x4C: (0x180035ED0, None, "runtime_class_init"), 0x5F: (0x1800036A0, None, "delegate_field_load"), 0x78: (0x1800036A0, None, "delegate_field_load"), 0xA4: (0x1800036A0, None, "delegate_field_load"), 0xB5: (0x18474F6F0, 489285, "BurstCompiler.GetILPPMethodFunctionPointer2"), 0xD2: (0x1800036A0, None, "delegate_field_load")}, "rip": [(0x15, 7, "initialization_guard"), (0x21, 7, "type_state"), (0x2D, 7, "runtime_method_handle"), (0x39, 7, "delegate_type_handle"), (0x45, 7, "runtime_type_handle"), (0x51, 7, "initialization_guard_store"), (0x58, 7, "delegate_state_load"), (0x64, 7, "delegate_state_load"), (0x7D, 7, "ilpp_method_load"), (0x84, 7, "runtime_method_handle_load"), (0x8B, 7, "delegate_type_handle_load"), (0x9D, 7, "initialization_state_load"), (0xBA, 7, "initialization_state_load"), (0xCB, 7, "initialization_state_load"), (0xD7, 7, "ilpp_method_load")], "indirect": []},
    385313: {"type": "BeyondDynamicBone.EndSimulationStepJobKernels+EndSimulationStepRangeKernel_000003BB$BurstDirectCall", "method": "GetFunctionPointer", "role": "collider_end_get_function_pointer", "va": 0x18675B078, "end": 0x18675B0CC, "sha": "d468db6b18d79b1fc74d0983bb696d1b03d67acc2fad0e95408492ef9fd76dbc", "calls": {0x14: (0x180035ED0, None, "runtime_class_init"), 0x39: (0x18002C880, None, "runtime_static_guard"), 0x45: (0x18675AF74, 385312, "GetFunctionPointerDiscard")}, "rip": [(0x04, 7, "initialization_guard"), (0x0D, 7, "initialization_state"), (0x19, 7, "initialization_guard_store"), (0x20, 7, "initialization_state_load")]},
    385312: {"type": "BeyondDynamicBone.EndSimulationStepJobKernels+EndSimulationStepRangeKernel_000003BB$BurstDirectCall", "method": "GetFunctionPointerDiscard", "role": "collider_end_get_function_pointer_discard", "va": 0x18675AF74, "end": 0x18675B078, "sha": "8b80e3fdd7d5a3624308497454cc81dc0e73e57ef983865bc06025982b155bf", "calls": {0x28: (0x180035ED0, None, "runtime_class_init"), 0x34: (0x180035ED0, None, "runtime_class_init"), 0x40: (0x180035ED0, None, "runtime_class_init"), 0x4C: (0x180035ED0, None, "runtime_class_init"), 0x5F: (0x1800036A0, None, "delegate_field_load"), 0x78: (0x1800036A0, None, "delegate_field_load"), 0xA4: (0x1800036A0, None, "delegate_field_load"), 0xB5: (0x18474F6F0, 489285, "BurstCompiler.GetILPPMethodFunctionPointer2"), 0xD2: (0x1800036A0, None, "delegate_field_load")}, "rip": [(0x15, 7, "initialization_guard"), (0x21, 7, "type_state"), (0x2D, 7, "runtime_method_handle"), (0x39, 7, "delegate_type_handle"), (0x45, 7, "runtime_type_handle"), (0x51, 7, "initialization_guard_store"), (0x58, 7, "delegate_state_load"), (0x64, 7, "delegate_state_load"), (0x7D, 7, "ilpp_method_load"), (0x84, 7, "runtime_method_handle_load"), (0x8B, 7, "delegate_type_handle_load"), (0x9D, 7, "initialization_state_load"), (0xBA, 7, "initialization_state_load"), (0xCB, 7, "initialization_state_load"), (0xD7, 7, "ilpp_method_load")], "indirect": []},
    385567: {"type": "BeyondDynamicBone.SimulationManager+StartSimulationStepJobKernels+StartSimulationStepRangeKernel_00000408$BurstDirectCall", "method": "Constructor", "role": "simulation_constructor", "va": 0x183FB21E0, "end": 0x183FB2270, "sha": "904e16fd75b3c4545842a059818a6f8f683d3e0b31f17245566b1270232a2576", "calls": {0x16: (0x180035ED0, None, "runtime_class_init"), 0x22: (0x180035ED0, None, "runtime_class_init"), 0x2E: (0x180035ED0, None, "runtime_class_init"), 0x51: (0x18002C880, None, "runtime_static_guard"), 0x5B: (0x183FB0BC0, 489284, "BurstCompiler.CompileILPPMethod2"), 0x73: (0x18002C880, None, "runtime_static_guard")}, "rip": []},
    385413: {"type": "BeyondDynamicBone.ColliderManager+StartSimulationStepJobKernels+StartSimulationStepRangeKernel_000003D8$BurstDirectCall", "method": "Constructor", "role": "collider_start_constructor", "va": 0x183FB2660, "end": 0x183FB26F0, "sha": "49cb396d03ef3d2687b4baf058b64d7cce9e0329166dc4e60d150ebe4889651b", "calls": {0x16: (0x180035ED0, None, "runtime_class_init"), 0x22: (0x180035ED0, None, "runtime_class_init"), 0x2E: (0x180035ED0, None, "runtime_class_init"), 0x51: (0x18002C880, None, "runtime_static_guard"), 0x5B: (0x183FB0BC0, 489284, "BurstCompiler.CompileILPPMethod2"), 0x73: (0x18002C880, None, "runtime_static_guard")}, "rip": []},
    385314: {"type": "BeyondDynamicBone.EndSimulationStepJobKernels+EndSimulationStepRangeKernel_000003BB$BurstDirectCall", "method": "Constructor", "role": "collider_end_constructor", "va": 0x183FB29C0, "end": 0x183FB2A50, "sha": "881b30b3a84115342ce43c696e20aa7c6578c5a0b6f91e11c84e8c7a0ee705c8", "calls": {0x16: (0x180035ED0, None, "runtime_class_init"), 0x22: (0x180035ED0, None, "runtime_class_init"), 0x2E: (0x180035ED0, None, "runtime_class_init"), 0x51: (0x18002C880, None, "runtime_static_guard"), 0x5B: (0x183FB0BC0, 489284, "BurstCompiler.CompileILPPMethod2"), 0x73: (0x18002C880, None, "runtime_static_guard")}, "rip": []},
    489283: {"type": "Unity.Burst.BurstCompiler", "method": "get_IsEnabled", "role": "burst_compiler_enabled", "va": 0x18307B8D0, "end": 0x18307B940, "sha": "5ebd6d7fab819f87fa679296ae3da3708c29760e0f2b0185b59f98b34ea69980", "calls": {}, "rip": []},
    489284: {"type": "Unity.Burst.BurstCompiler", "method": "CompileILPPMethod2", "role": "burst_compiler_ilpp_init", "va": 0x183FB0BC0, "end": 0x183FB0CA0, "sha": "8ab80ebd0afe065d38f9c3473b6bcd080831d913cd77e7fae80bad3c0d81406a", "calls": {0xA1: (0x183FB0D30, 489288, "BurstCompiler.Compile")}, "rip": []},
    489285: {"type": "Unity.Burst.BurstCompiler", "method": "GetILPPMethodFunctionPointer2", "role": "burst_compiler_function_pointer", "va": 0x18474F6F0, "end": 0x18474F720, "sha": "9bee5e8ec8df54600135338af3dcfb9bd658c504be3b76c5dd27f1093c44cc24", "calls": {}, "rip": []},
    489288: {"type": "Unity.Burst.BurstCompiler", "method": "Compile", "role": "burst_compiler_service_bridge", "va": 0x183FB0D30, "end": 0x183FB0FD0, "sha": "c77723c44e300e7a3857c87ad46799dcf7c8600b2b1e23d61d13f31dda95efe9", "calls": {0x136: (0x183FB1010, 402096, "BurstCompilerService.CompileAsyncDelegateMethod"), 0x13F: (0x183FB0FD0, 402097, "BurstCompilerService.GetAsyncCompiledAsyncDelegateMethod")}, "rip": []},
    402096: {"type": "Unity.Burst.LowLevel.BurstCompilerService", "method": "CompileAsyncDelegateMethod", "role": "burst_compiler_service_compile_async", "va": 0x183FB1010, "end": 0x183FB1060, "sha": "11292831a98144c83876fef614792cea95d5d814a41eb9a5c9ed993f59d870a9", "calls": {0x36: (0x180059FC0, None, "late_bound_native_service_factory")}, "rip": [(0x0A, 7, "service_function_slot"), (0x2F, 7, "service_factory_string_or_slot"), (0x44, 7, "service_function_slot_store")]},
    402097: {"type": "Unity.Burst.LowLevel.BurstCompilerService", "method": "GetAsyncCompiledAsyncDelegateMethod", "role": "burst_compiler_service_get_async", "va": 0x183FB0FD0, "end": 0x183FB1010, "sha": "baa29c1b316ca0b19e357d5c2706ee037fc5869dbdd673818ffea2b0a16f7254", "calls": {0x25: (0x180059FC0, None, "late_bound_native_service_factory")}, "rip": [(0x06, 7, "service_function_slot"), (0x1E, 7, "service_factory_string_or_slot"), (0x33, 7, "service_function_slot_store")]},
}


TARGET_SPECS[385312]["sha"] = "8b80e3fdd7d5a3624308497454cc81dc0e73e57e90c5e3596caf17b941950c7a"


def _decode_rel32(body: bytes, offset: int, opcode: int) -> int:
    if offset < 0 or offset + 5 > len(body) or body[offset] != opcode:
        raise ContractError(f"expected rel32 opcode 0x{opcode:02x} at body offset 0x{offset:x}")
    return struct.unpack_from("<i", body, offset + 1)[0]


def _direct_target(va: int, body: bytes, offset: int) -> int:
    return va + offset + 5 + _decode_rel32(body, offset, 0xE8)


def _rip_target(va: int, body: bytes, offset: int, length: int) -> int:
    if offset < 0 or offset + length > len(body) or length < 4:
        raise ContractError(f"RIP site at 0x{offset:x} is outside body")
    # cmp byte [rip+disp32],imm8 and mov byte [rip+disp32],imm8 place the
    # displacement at byte two; lea/mov qword [rip+disp32] place it at the
    # final four bytes of the instruction.
    displacement_offset = offset + 2 if body[offset] in (0x80, 0xC6) else offset + length - 4
    displacement = struct.unpack_from("<i", body, displacement_offset)[0]
    return va + offset + length + displacement


def _indirect_encoding(register: str) -> bytes:
    # The wrappers use the register returned by GetFunctionPointer.  These
    # exact bytes keep the contract independent of a disassembler dependency.
    return {"rax": b"\xff\xd0", "rdx": b"\xff\xd2", "r10": b"\x41\xff\xd2"}[register]


def _exports(path: Path) -> dict[str, Any]:
    """Read only the PE export directory; arbitrary 32-hex strings are not exports."""
    data = path.read_bytes()
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ContractError("lib_burst_generated.dll is not a PE image")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset + 24 > len(data) or data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ContractError("lib_burst_generated.dll has no PE signature")
    coff = pe_offset + 4
    section_count = struct.unpack_from("<H", data, coff + 2)[0]
    optional_size = struct.unpack_from("<H", data, coff + 16)[0]
    optional = coff + 20
    if optional + optional_size > len(data) or struct.unpack_from("<H", data, optional)[0] != 0x20B:
        raise ContractError("lib_burst_generated.dll is not PE32+")
    export_rva, export_size = struct.unpack_from("<II", data, optional + 112)
    if not export_rva or export_size < 40:
        raise ContractError("lib_burst_generated.dll has no export directory")
    section_table = optional + optional_size
    sections: list[tuple[int, int, int]] = []
    for index in range(section_count):
        row = section_table + index * 40
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from("<IIII", data, row + 8)
        sections.append((virtual_address, max(virtual_size, raw_size), raw_pointer))

    def rva_offset(rva: int, size: int = 1) -> int:
        for va, section_size, raw in sections:
            if va <= rva and rva + size <= va + section_size:
                offset = raw + rva - va
                if 0 <= offset <= len(data) - size:
                    return offset
        raise ContractError(f"export RVA 0x{rva:x} is outside PE sections")

    directory = rva_offset(export_rva, 40)
    (_characteristics, _timestamp, _major, _minor, _name_rva, _ordinal_base,
     _function_count, name_count, _functions_rva, names_rva,
     _ordinals_rva) = struct.unpack_from("<IIHHIIIIIII", data, directory)
    names: list[bytes] = []
    for index in range(name_count):
        name_rva = struct.unpack_from("<I", data, rva_offset(names_rva + index * 4, 4))[0]
        start = rva_offset(name_rva)
        end = data.find(b"\0", start)
        if end < 0:
            raise ContractError("unterminated hashed export name")
        value = data[start:end]
        if re.fullmatch(rb"[0-9a-f]{32}", value):
            names.append(value)
    names = sorted(set(names))
    if not names:
        raise ContractError("no 32-hex Burst exports found")
    return {
        "count": len(names),
        "namesSha256": hashlib.sha256(b"\n".join(names)).hexdigest(),
    }


def _string_evidence(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    prefix_counts: dict[str, int] = {}
    hashes: set[bytes] = set()
    for prefix in (b"externals", b"statics"):
        matches = re.findall(rb"burst\.initialize\." + prefix + rb"\.([0-9a-f]{32})_(?:avx2|x64_sse2)", data)
        prefix_counts[prefix.decode()] = len(set(matches))
        hashes.update(matches)
    pdb = b"Beyond.Editor_Data\\\\Plugins\\\\x86_64\\\\lib_burst_generated.pdb" in data
    return {
        "initializationPrefixes": ["burst.initialize.externals", "burst.initialize.statics"],
        "distinctHashesPerPrefix": prefix_counts,
        "distinctInitializationHashes": len(hashes),
        "pdbPathStringObserved": pdb,
        "mappingUse": "initializer strings establish the Burst-generated naming scheme only; they do not join a GameAssembly wrapper to one hash",
    }


def _native_gate(gameassembly: Path | None, metadata: Path | None) -> tuple[dict[str, Any], Path]:
    result = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if not result.validated:
        raise ContractError(f"common.check_installed_native_inputs [{result.status}]: {result.detail}")
    ga = Path(result.gameassembly)
    md = Path(result.metadata)
    burst = ga.parent / "Endfield_Data/Plugins/x86_64/lib_burst_generated.dll"
    if not burst.is_file():
        raise ContractError(f"missing lib_burst_generated.dll: {burst}")
    burst_hash = _sha256(burst)
    if burst_hash != EXPECTED_LIB_BURST_SHA256:
        raise ContractError(f"lib_burst_generated.dll sha256 mismatch: {burst_hash}")
    return {
        "gameAssembly": _file(ga, result.gameassembly_sha256),
        "globalMetadata": _file(md, result.metadata_sha256),
        "libBurstGenerated": _file(burst, burst_hash),
    }, burst


def _known_method_index(method_by_pointer: dict[int, list[dict[str, Any]]], va: int) -> int | None:
    rows = method_by_pointer.get(va, [])
    indexes = {int(row["methodIndex"]) for row in rows}
    return next(iter(indexes)) if len(indexes) == 1 else None


def _verify_target(
    method_index: int,
    spec: dict[str, Any],
    native: Any,
    md: Any,
    pe: Any,
    method_by_pointer: dict[int, list[dict[str, Any]]],
    all_pointers: list[int],
) -> dict[str, Any]:
    matches = _register_method_rows(method_by_pointer, method_index)
    if len(matches) != 1:
        raise ContractError(f"method {method_index} resolves to {len(matches)} native pointers")
    pointer, signature = matches[0]
    if pointer != spec["va"]:
        raise ContractError(f"method {method_index} VA drift: {_hex(pointer)} != {_hex(spec['va'])}")
    if signature.get("type") != spec["type"] or signature.get("method") != spec["method"] or not _method_label_matches(md, method_index, spec["type"], spec["method"]):
        raise ContractError(f"method {method_index} metadata identity drift")
    if bisect_right(all_pointers, pointer) >= len(all_pointers) or all_pointers[bisect_right(all_pointers, pointer)] != spec["end"]:
        raise ContractError(f"method {method_index} next pointer drift")
    body = pe.bytes_at_va(pointer, spec["end"] - pointer)
    if len(body) != spec["end"] - pointer:
        raise ContractError(f"method {method_index} body is truncated")
    actual_hash = hashlib.sha256(body).hexdigest()
    if actual_hash != spec["sha"]:
        raise ContractError(f"method {method_index} body hash drift: {actual_hash}")

    calls: list[dict[str, Any]] = []
    for offset, (expected_target, expected_method, kind) in sorted(spec.get("calls", {}).items()):
        actual_target = _direct_target(pointer, body, offset)
        if actual_target != expected_target:
            raise ContractError(f"method {method_index} direct call 0x{offset:x} drift: {_hex(actual_target)} != {_hex(expected_target)}")
        actual_method = _known_method_index(method_by_pointer, actual_target)
        if expected_method is not None and actual_method != expected_method:
            raise ContractError(f"method {method_index} call 0x{offset:x} identity drift: {actual_method} != {expected_method}")
        calls.append({"instructionOffset": _hex(offset), "targetVa": _hex(actual_target), "kind": kind, **({"methodIndex": actual_method} if actual_method is not None else {})})

    rip_globals: list[dict[str, Any]] = []
    for offset, length, kind in spec.get("rip", []):
        target = _rip_target(pointer, body, offset, length)
        rip_globals.append({"instructionOffset": _hex(offset), "targetVa": _hex(target), "kind": kind})

    indirect_calls: list[dict[str, Any]] = []
    for offset, register, kind in spec.get("indirect", []):
        encoding = _indirect_encoding(register)
        if body[offset:offset + len(encoding)] != encoding:
            raise ContractError(f"method {method_index} indirect call 0x{offset:x} encoding drift")
        indirect_calls.append({"instructionOffset": _hex(offset), "register": register, "kind": kind, "encoding": encoding.hex()})

    row: dict[str, Any] = {
        "methodIndex": method_index,
        "type": signature["type"],
        "method": signature["method"],
        "token": signature.get("token"),
        "returnType": signature.get("returnTypeName"),
        "role": spec["role"],
        "va": _hex(pointer),
        "endVaExclusive": _hex(spec["end"]),
        "spanBytes": spec["end"] - pointer,
        "bodySha256": actual_hash,
        "directCalls": calls,
    }
    if rip_globals:
        row["ripGlobals"] = rip_globals
    if indirect_calls:
        row["indirectCalls"] = indirect_calls
    return row


def _verify_cctor(pe: Any, method_by_pointer: dict[int, list[dict[str, Any]]], all_pointers: list[int], method_index: int, expected_target: int, expected_target_method: int) -> dict[str, Any]:
    rows = _register_method_rows(method_by_pointer, method_index)
    if len(rows) != 1:
        raise ContractError(f"cctor {method_index} resolves to {len(rows)} pointers")
    pointer, _signature = rows[0]
    index = bisect_right(all_pointers, pointer)
    if index >= len(all_pointers):
        raise ContractError(f"cctor {method_index} has no bounded end")
    body = pe.bytes_at_va(pointer, all_pointers[index] - pointer)
    if body[:2] != b"\x33\xc9":
        raise ContractError(f"cctor {method_index} does not clear the static constructor argument")
    target = pointer + 2 + 5 + _decode_rel32(body, 2, 0xE9)
    if target != expected_target:
        raise ContractError(f"cctor {method_index} tail jump drift")
    actual_target_method = _known_method_index(method_by_pointer, target)
    if actual_target_method != expected_target_method:
        raise ContractError(f"cctor {method_index} constructor identity drift")
    return {"methodIndex": method_index, "tailJumpTargetVa": _hex(target), "targetMethodIndex": actual_target_method}


def build_contract(*, gameassembly: Path | None = DEFAULT_GAME_ASSEMBLY, metadata: Path | None = DEFAULT_METADATA) -> dict[str, Any]:
    gate, burst = _native_gate(gameassembly, metadata)
    native, md, pe, method_by_pointer, all_pointers, metadata_registration = _native_indexes(Path(gate["globalMetadata"]["path"]), Path(gate["gameAssembly"]["path"]))
    targets = [_verify_target(index, spec, native, md, pe, method_by_pointer, all_pointers) for index, spec in TARGET_SPECS.items()]
    cctors = [
        _verify_cctor(pe, method_by_pointer, all_pointers, 385569, 0x183FB21E0, 385567),
        _verify_cctor(pe, method_by_pointer, all_pointers, 385415, 0x183FB2660, 385413),
        _verify_cctor(pe, method_by_pointer, all_pointers, 385316, 0x183FB29C0, 385314),
    ]
    exports = _exports(burst)
    strings = _string_evidence(burst)
    return {
        "schema": "endfield.charinfo.secondary-dynamics-burst-wrapper.v1",
        "status": "initialization_resolution_chain_closed_export_mapping_unresolved",
        "nativeGate": gate,
        "registration": {"codeRegistrationVa": _hex(EXPECTED_CODE_REGISTRATION), "metadataRegistrationVa": _hex(metadata_registration)},
        "staticEvidence": {
            "methodIdentitySource": "global-metadata.dat method records joined to code-registration method_by_pointer",
            "spanBoundarySource": "next sorted all_pointers entry after each resolved method pointer",
            "bodyEvidenceSource": "GameAssembly.dll PE bytes bounded by the adjacent all_pointers span",
            "hash": "SHA-256 of each bounded PE body",
            "directCallEvidence": "x64 E8 rel32 bytes at the recorded instruction offsets",
            "ripGlobalEvidence": "x64 RIP-relative displacement bytes at the recorded instruction offsets",
        },
        "targets": targets,
        "staticConstructors": cctors,
        "resolutionPath": {
            "status": "BurstCompiler_to_late_bound_BurstCompilerService",
            "managedBurstCompilerMethods": [489283, 489284, 489285, 489288],
            "burstCompilerServiceMethods": [402096, 402097],
            "lateBoundNativeServiceFactoryVa": _hex(0x180059FC0),
            "getProcAddressObservedStatically": False,
            "runtimeTelemetryRequired": True,
            "runtimeTelemetry": {
                "hookConfig": "unity_endfield_graph_shader_lab/config/burst_resolver_telemetry_hooks.json",
                "events": ["LoadLibraryW", "GetProcAddress"],
                "moduleGate": "the HMODULE returned for the pinned lib_burst_generated.dll",
            },
            "reason": "GameAssembly wrappers and service thunks expose no unique 32-hex export name; the service factory and GetProcAddress must be observed at runtime for the selected lib_burst_generated.dll HMODULE.",
        },
        "burstGenerated": {
            **exports,
            "stringEvidence": strings,
            "mappingStatus": "unresolved_wrapper_to_hashed_export",
            "candidateBoundary": "all names in the pinned IMAGE_EXPORT_DIRECTORY are bounded candidates; no candidate is promoted without runtime GetProcAddress evidence",
        },
        "unresolved": [
            {"boundary": "385570 simulation wrapper to lib_burst_generated.dll export", "status": "unresolved", "boundedCandidates": exports["count"]},
            {"boundary": "385394 collider-start wrapper to lib_burst_generated.dll export", "status": "unresolved", "boundedCandidates": exports["count"]},
            {"boundary": "385295 collider-end wrapper to lib_burst_generated.dll export", "status": "unresolved", "boundedCandidates": exports["count"]},
        ],
    }


def _markdown(contract: dict[str, Any]) -> str:
    lines = [
        "# Secondary dynamics BurstDirectCall wrapper contract",
        "",
        f"Status: `{contract['status']}`.",
        "",
        "The pinned GameAssembly/metadata registration and Burst DLL export directory close the managed wrapper and BurstCompilerService path. The final hashed export remains unresolved: all 628 export-directory names are bounded candidates until runtime GetProcAddress telemetry observes the selected HMODULE/name.",
        "",
        "| Method | Role | Span | Direct calls |",
        "|---:|---|---|---|",
    ]
    for row in contract["targets"]:
        calls = ", ".join(f"{call.get('methodIndex', call['targetVa'])} @ {call['instructionOffset']}" for call in row["directCalls"]) or "-"
        lines.append(f"| {row['methodIndex']} | {row['role']} | `{row['va']}..{row['endVaExclusive']}` ({row['spanBytes']} B) | {calls} |")
    lines += ["", "No wrapper-to-hash mapping is asserted. The generated contract records the complete bounded candidate count/hash and preserves runtime telemetry as the required next gate.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--check", action="store_true", help="verify checked-in JSON and Markdown without writing")
    args = parser.parse_args()
    try:
        contract = build_contract(gameassembly=args.gameassembly, metadata=args.metadata)
    except ContractError as exc:
        print(f"[secondary-dynamics-burst-wrapper] {exc}", file=sys.stderr)
        return 2
    if args.check:
        if not args.output.is_file() or not args.markdown.is_file():
            print("[secondary-dynamics-burst-wrapper] checked-in output is missing", file=sys.stderr)
            return 2
        if json.loads(args.output.read_text(encoding="utf-8")) != contract:
            print("[secondary-dynamics-burst-wrapper] JSON output is stale", file=sys.stderr)
            return 2
        if args.markdown.read_text(encoding="utf-8") != _markdown(contract):
            print("[secondary-dynamics-burst-wrapper] Markdown output is stale", file=sys.stderr)
            return 2
        print(f"checked {args.output} and {args.markdown}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown(contract), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
