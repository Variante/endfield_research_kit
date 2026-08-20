#!/usr/bin/env python3
"""Pin the static Execute/UnsafeDo boundary for secondary-dynamics jobs.

This is deliberately a *boundary* contract.  ``Execute()`` is the managed
enumerator wrapper and ``UnsafeDo()`` is a Burst range-dispatch wrapper.  The
contract never labels either as the solver.  Only the indexed managed
``Execute(int)`` bodies below are classified as managed fallbacks, and their
raw buffer arithmetic is recorded as evidence.  The Burst implementation is
left unresolved until its generated function is independently identified.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import copy
import struct
import sys
from bisect import bisect_right
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_solver_static_contract.json"
DEFAULT_MARKDOWN = SOURCE_ROOT / "secondary_dynamics_solver_static_contract.md"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    """Raised when the pinned native evidence no longer matches."""


def _pe_image_module() -> Any:
    path = REPO_ROOT / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py"
    spec = importlib.util.spec_from_file_location("endfield_solver_pe_image", path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load PE helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _hex(value: int) -> str:
    return f"0x{value:x}"


def _target(
    method_index: int,
    type_name: str,
    method: str,
    role: str,
    va: int,
    end_va: int,
    sha256: str,
    next_calls: list[dict[str, Any]],
    *,
    accesses: list[dict[str, Any]] | None = None,
    solver_status: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "methodIndex": method_index,
        "type": type_name,
        "method": method,
        "role": role,
        "solverStatus": solver_status,
        "va": _hex(va),
        "endVaExclusive": _hex(end_va),
        "spanBytes": end_va - va,
        "bodySha256": sha256,
        "nextCalls": next_calls,
    }
    if accesses is not None:
        row["bufferAccesses"] = accesses
    return row


def _managed_call(
    method_index: int,
    va: int,
    name: str,
    role: str,
    instruction_offsets: list[int] | None = None,
) -> dict[str, Any]:
    row = {"kind": role, "methodIndex": method_index, "va": _hex(va), "method": name}
    if instruction_offsets is not None:
        row["instructionOffsets"] = [_hex(offset) for offset in instruction_offsets]
    return row


SIM = "BeyondDynamicBone.SimulationManager"
COL = "BeyondDynamicBone.ColliderManager"
SIM_START = f"{SIM}+StartSimulationStepJob"
SIM_END = f"{SIM}+EndSimulationStepJob"
COL_START = f"{COL}+StartSimulationStepJob"
COL_END = f"{COL}+EndSimulationStepJob"

EXPECTED_CODE_REGISTRATION = 0x18B9217D0


def _load_helper(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load native helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _native_indexes(metadata: Path, gameassembly: Path) -> tuple[Any, Any, Any, dict[int, list[dict[str, Any]]], list[int]]:
    root = REPO_ROOT / "tools/endfield-il2cpp"
    catalog = _load_helper("secondary_solver_metadata", root / "catalog_option_flow_metadata.py")
    native = _load_helper("secondary_solver_native", root / "map_body_targets_to_gameassembly.py")
    md = catalog.Metadata(metadata)
    pe = native.PeImage(gameassembly)
    image_names = {md.string(image.name_index) for image in md.images}
    code_registration = native.find_code_registration(pe, image_names)
    if code_registration != EXPECTED_CODE_REGISTRATION:
        raise ContractError(
            f"code registration drift: {code_registration!r} != {_hex(EXPECTED_CODE_REGISTRATION)}"
        )
    modules = native.parse_codegen_modules(pe, code_registration)
    ranges = native.image_method_ranges(md)
    _pointers_by_image, method_by_pointer = native.build_pointer_indexes(pe, md, modules, ranges)
    all_pointers = sorted(pointer for pointer in method_by_pointer if pointer)
    return native, md, pe, method_by_pointer, all_pointers


def _register_method_rows(
    method_by_pointer: dict[int, list[dict[str, Any]]],
    method_index: int,
) -> list[tuple[int, dict[str, Any]]]:
    return [
        (pointer, signature)
        for pointer, signatures in method_by_pointer.items()
        for signature in signatures
        if int(signature.get("methodIndex", -1)) == method_index
    ]


def _method_label_matches(md: Any, method_index: int, label: str) -> bool:
    """Match a display overload label against the metadata method record."""
    method = md.methods[method_index]
    display_type = ""
    if "." in label and not label.startswith("Execute"):
        display_type, label = label.rsplit(".", 1)
    name, _, overload = label.partition("(")
    if md.string(method.name_index) != name:
        return False
    if display_type and not md.type_full_name(md.types[method.declaring_type]).endswith(display_type):
        return False
    if not overload:
        return True
    if not overload.endswith(")"):
        return False
    parameter_names = [md.metadata_type_name(param.type_index) for param in md.parameters_for(method)]
    expected = [part.strip() for part in overload[:-1].split(",") if part.strip()]
    aliases = {"int": "System.Int32", "float": "System.Single", "double": "System.Double"}
    expected = [aliases.get(part, part) for part in expected]
    return parameter_names == expected


def _reg_name(code: int) -> str:
    names = (
        "rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
        "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
    )
    return names[code]


def _memory_instruction(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode the small x64 memory/imul subset used by these job bodies."""
    pos = offset
    prefixes: list[int] = []
    while pos < len(data) and data[pos] in (0x66, 0xF2, 0xF3):
        prefixes.append(data[pos])
        pos += 1
    rex = 0
    if pos < len(data) and 0x40 <= data[pos] <= 0x4F:
        rex = data[pos]
        pos += 1
    if pos >= len(data):
        return None
    opcode = data[pos]
    pos += 1
    opcode2: int | None = None
    if opcode == 0x0F:
        if pos >= len(data):
            return None
        opcode2 = data[pos]
        pos += 1
    if opcode == 0x69:
        if pos + 5 > len(data):
            return None
        modrm = data[pos]
        mod = modrm >> 6
        pos += 1
        if mod == 3:
            pass
        elif (modrm & 7) == 4:
            if pos >= len(data):
                return None
            sib = data[pos]
            pos += 1
            if mod == 0 and (sib & 7) == 5:
                pos += 4
            elif mod == 1:
                pos += 1
            elif mod == 2:
                pos += 4
        elif mod == 0 and (modrm & 7) == 5:
            pos += 4
        elif mod == 1:
            pos += 1
        elif mod == 2:
            pos += 4
        if pos + 4 > len(data):
            return None
        return {"kind": "imul", "immediate": struct.unpack_from("<i", data, pos)[0]}

    memory_opcodes = {
        (None, 0x8A): 1, (None, 0x88): 1, (None, 0x8B): 8 if rex & 8 else 4,
        (None, 0x89): 8 if rex & 8 else 4, (None, 0x63): 4,
        (None, 0x03): 8 if rex & 8 else 4,
        (0x10, 0x0F): 16, (0x11, 0x0F): 16,
    }
    # The two-byte opcode table above is keyed by (opcode2, opcode1).
    if opcode2 is None:
        width = memory_opcodes.get((None, opcode))
    else:
        width = {
            0x10: 4 if 0xF3 in prefixes else 8 if 0xF2 in prefixes else 16,
            0x11: 4 if 0xF3 in prefixes else 8 if 0xF2 in prefixes else 16,
            0x6F: 16,
            0x7F: 16,
            0xBF: 2,
        }.get(opcode2)
    if width is None or pos >= len(data):
        return None
    modrm = data[pos]
    mod, _reg, rm = (modrm >> 6) & 3, (modrm >> 3) & 7, modrm & 7
    if mod == 3:
        return None
    pos += 1
    rex_b = rex & 1
    rex_x = (rex >> 1) & 1
    base_code: int | None = (rm | (rex_b << 3))
    index_code: int | None = None
    scale = 1
    if rm == 4:
        if pos >= len(data):
            return None
        sib = data[pos]
        pos += 1
        scale = 1 << (sib >> 6)
        raw_index = (sib >> 3) & 7
        index_code = None if raw_index == 4 and not rex_x else raw_index | (rex_x << 3)
        raw_base = sib & 7
        base_code = None if mod == 0 and raw_base == 5 else raw_base | (rex_b << 3)
    elif mod == 0 and rm == 5:
        base_code = None
    if mod == 0 and (rm != 4 or (data[pos - 1] & 7) == 5):
        displacement = 0
        if rm == 4 and (data[pos - 1] & 7) == 5 or rm == 5:
            if pos + 4 > len(data):
                return None
            displacement = struct.unpack_from("<i", data, pos)[0]
            pos += 4
    elif mod == 1:
        if pos + 1 > len(data):
            return None
        displacement = struct.unpack_from("<b", data, pos)[0]
        pos += 1
    elif mod == 2:
        if pos + 4 > len(data):
            return None
        displacement = struct.unpack_from("<i", data, pos)[0]
        pos += 4
    else:
        displacement = 0
    return {
        "kind": "memory",
        "base": _reg_name(base_code) if base_code is not None else None,
        "index": _reg_name(index_code) if index_code is not None else None,
        "scale": scale,
        "displacement": displacement,
        "width": width,
    }


# VAs/spans are method-pointer boundaries from the pinned code-registration
# map.  Hashing exactly this interval also prevents a neighboring method from
# being accidentally treated as part of a body.
TARGETS = [
    _target(385696, SIM_START, "Execute", "managed_dispatch_wrapper", 0x186775A4C, 0x186775AE4,
            "26b144cda78f3f0f48cbdb9ce8f3883f8494bde58e2aa05e3363bb203e20a697",
            [_managed_call(385697, 0x186774BE8, "Execute(int)", "managed_fallback", [0x56])],
            solver_status="wrapper_only"),
    _target(385697, SIM_START, "Execute(int)", "managed_fallback", 0x186774BE8, 0x186775A4C,
            "08fca10086f3b997dd895476d17f930b2ab66d8c63bf9462c8849b56d6edcf0a",
            [_managed_call(385698, 0x186775AE4, "Spring", "managed_helper", [0xDB2]),
             _managed_call(385699, 0x186776704, "Wind", "managed_helper", [0xBDA])],
            accesses=[
                {"jobField": "stepParticleIndexArray", "jobOffset": "0x18", "index": "Execute(index)", "strideBytes": 4, "elementFieldDisplacements": [0], "instructionOffsets": ["0xe9"]},
                {"jobField": "teamIdArray", "jobOffset": "0xc8", "index": "particleIndex", "strideBytes": 2, "elementFieldDisplacements": [0], "instructionOffsets": ["0xf8"]},
                {"jobField": "teamDataArray", "jobOffset": "0x78", "index": "teamId", "strideBytes": 464, "elementFieldDisplacements": [0, 16, 32, 48, 64, 80, 96, 112], "instructionOffsets": ["0xfd", "0x10e", "0x111", "0x118", "0x120", "0x128", "0x130", "0x138", "0x140"]},
                {"jobField": "parameterArray", "jobOffset": "0x88", "index": "teamId", "strideBytes": 808, "elementFieldDisplacements": [0, 16, 32, 48, 64, 80, 96, 112], "instructionOffsets": ["0x28e", "0x29f", "0x2a5", "0x2ad", "0x2b5", "0x2bd", "0x2c5", "0x2cd", "0x2d8"]},
                {"jobField": "attributes", "jobOffset": "0x28", "index": "derivedVertexIndex", "strideBytes": 1, "elementFieldDisplacements": [0], "instructionOffsets": ["0x318"]},
                {"jobField": "depthArray", "jobOffset": "0x38", "index": "derivedVertexIndex", "strideBytes": 4, "elementFieldDisplacements": [0], "instructionOffsets": ["0x328"]},
                {"jobField": "oldPosArray", "jobOffset": "0xd8", "index": "particleIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x339", "0x33e"]},
                {"jobField": "oldPositionArray", "jobOffset": "0x128", "index": "particleIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x39b", "0x39f"]},
                {"jobField": "positions", "jobOffset": "0x48", "index": "derivedVertexIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x37c", "0x380"]},
                {"jobField": "rotations", "jobOffset": "0x58", "index": "derivedVertexIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x36c"]},
                {"jobField": "basePosArray", "jobOffset": "0xf8", "index": "particleIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x42a", "0x42e"]},
                {"jobField": "baseRotArray", "jobOffset": "0x118", "index": "particleIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x445"]},
                {"jobField": "stepBasicPositionArray", "jobOffset": "0x168", "index": "particleIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x45e", "0x462"]},
                {"jobField": "stepBasicRotationArray", "jobOffset": "0x178", "index": "particleIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x479"]},
                {"jobField": "velocityPosArray", "jobOffset": "0x148", "index": "particleIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0xdc2", "0xdc6"]},
                {"jobField": "nextPosArray", "jobOffset": "0xe8", "index": "particleIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0xde1", "0xde5"]},
            ],
            solver_status="managed_fallback_observed"),
    _target(385698, SIM_START, "Spring", "managed_helper", 0x186775AE4, 0x186776080,
            "149382eea39d5d1a3ca0e27ed701a665f51406664766283b070305adc52050b5", [],
            solver_status="helper_only"),
    _target(385699, SIM_START, "Wind", "managed_helper", 0x186776704, 0x186776B64,
            "2aca620c9c194d06742ffcc855efd57cca85bee46a8fc972da83ff02a855b0a0",
            [_managed_call(385700, 0x186776394, "WindForceBlend", "managed_helper", [0x28A, 0x318])],
            solver_status="helper_only"),
    _target(385700, SIM_START, "WindForceBlend", "managed_helper", 0x186776394, 0x186776704,
            "0418400aa5d180fb7e81233ae707325e580d9881ffd519b0953e72ca9bce8796", [],
            solver_status="helper_only"),
    _target(385701, SIM_START, "UnsafeDo", "burst_range_dispatch_wrapper", 0x186776080, 0x186776394,
            "872a5aefd318ed907b800bb0c5a982cce47de2298019a3615416a8539da0944f",
            [_managed_call(385542, 0x1867744B0, "StartSimulationStepRangeKernel", "burst_wrapper", [0x2A2]),
             _managed_call(385570, 0x1867775FC, "StartSimulationStepRangeKernel_00000408$BurstDirectCall.Invoke", "burst_invoke")],
            solver_status="wrapper_only_burst_solver_unresolved"),
    _target(385450, COL_START, "Execute", "managed_dispatch_wrapper", 0x186761580, 0x186761618,
            "11f3c6969dddd71698113711000f247f6adb4ade024af45c4f8d5adec260503d",
            [_managed_call(385451, 0x186761618, "Execute(int)", "managed_fallback", [0x56])], solver_status="wrapper_only"),
    _target(385451, COL_START, "Execute(int)", "managed_fallback", 0x186761618, 0x1867624AC,
            "61d0b5400bed687be8baa7bf5281119b2ce09276423b84461fc27053710c7426",
            [], accesses=[
                {"jobField": "jobColliderIndexList", "jobOffset": "0x0", "index": "Execute(index)", "strideBytes": 4, "elementFieldDisplacements": [0], "instructionOffsets": ["0x84"]},
                {"jobField": "flagArray", "jobOffset": "0x40", "index": "colliderIndex", "strideBytes": 1, "elementFieldDisplacements": [0], "instructionOffsets": ["0x8c"]},
                {"jobField": "teamIdArray", "jobOffset": "0x30", "index": "colliderIndex", "strideBytes": 2, "elementFieldDisplacements": [0], "instructionOffsets": ["0xb4"]},
                {"jobField": "teamDataArray", "jobOffset": "0x10", "index": "teamId", "strideBytes": 464, "elementFieldDisplacements": [0, 16, 32, 48, 64, 80, 96, 112], "instructionOffsets": ["0xb9", "0xc4", "0xcb", "0xce", "0xd5", "0xdd", "0xe5", "0xed", "0xf5", "0xfd"]},
                {"jobField": "centerDataArray", "jobOffset": "0x20", "index": "teamId", "strideBytes": 696, "elementFieldDisplacements": [0], "instructionOffsets": ["0x280"]},
                {"jobField": "framePositions", "jobOffset": "0x60", "index": "colliderIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x155", "0x159"]},
                {"jobField": "oldFramePositions", "jobOffset": "0x90", "index": "colliderIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x178", "0x17c"]},
                {"jobField": "nowPositions", "jobOffset": "0xb0", "index": "colliderIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x2a0", "0x2a5"]},
                {"jobField": "nowRotations", "jobOffset": "0xc0", "index": "colliderIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x2ba"]},
                {"jobField": "oldPositions", "jobOffset": "0xd0", "index": "colliderIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x34b", "0x34f"]},
                {"jobField": "oldRotations", "jobOffset": "0xe0", "index": "colliderIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x420"]},
                {"jobField": "workDataArray", "jobOffset": "0xf0", "index": "teamId", "strideBytes": 184, "elementFieldDisplacements": [0, 16, 32, 48, 64, 80, 96], "instructionOffsets": ["0xdaa", "0xdb8", "0xdbf", "0xdc7", "0xdcf", "0xdd7", "0xddf", "0xde7"]},
            ], solver_status="managed_fallback_observed"),
    _target(385452, COL_START, "UnsafeDo", "burst_range_dispatch_wrapper", 0x1867624AC, 0x1867626D4,
            "a1c75cee6d57da2caeb51378eef44c5e7e070a63088a09920a2373dfe20f682b",
            [_managed_call(385394, 0x186761454, "StartSimulationStepRangeKernel", "burst_wrapper", [0x1B3])], solver_status="wrapper_only_burst_solver_unresolved"),
    _target(385454, COL_END, "Execute", "managed_dispatch_wrapper", 0x18675AA6C, 0x18675AB00,
            "82212005e41ac5518f49cdcdc8e3f3403c549899bd7042d70891b4ec3988cda5",
            [_managed_call(385455, 0x18675A9CC, "Execute(int)", "managed_fallback", [0x53])], solver_status="wrapper_only"),
    _target(385455, COL_END, "Execute(int)", "managed_fallback", 0x18675A9CC, 0x18675AA6C,
            "f1c0ba8d18fa324f21aafd9c791f7658c7238d4bc4bfcacc5f1cd96268c8b297", [], accesses=[
                {"jobField": "jobColliderIndexList", "jobOffset": "0x0", "index": "Execute(index)", "strideBytes": 4, "elementFieldDisplacements": [0], "instructionOffsets": ["0x23"]},
                {"jobField": "nowPositions", "jobOffset": "0x10", "index": "colliderIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x35", "0x2f"]},
                {"jobField": "oldPositions", "jobOffset": "0x30", "index": "colliderIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x41", "0x45"]},
                {"jobField": "nowRotations", "jobOffset": "0x20", "index": "colliderIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x55"]},
                {"jobField": "oldRotations", "jobOffset": "0x40", "index": "colliderIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x64"]},
            ], solver_status="managed_fallback_observed"),
    _target(385456, COL_END, "UnsafeDo", "burst_range_dispatch_wrapper", 0x18675AB00, 0x18675ABBC,
            "b8700fd30831d687414b987c03978d19b382aa2723816bc63e4fa2ce1e00c9b1",
            [_managed_call(385295, 0x18675A944, "EndSimulationStepRangeKernel", "burst_wrapper", [0x84])], solver_status="wrapper_only_burst_solver_unresolved"),
]


def _verify_buffer_access(pe: Any, row: dict[str, Any], access: dict[str, Any]) -> None:
    start = int(row["va"], 16)
    span = int(row["spanBytes"])
    body = pe.bytes_at_va(start, span)
    offsets = [int(value, 16) for value in access["instructionOffsets"]]
    if not offsets or any(offset < 0 or offset >= span for offset in offsets):
        raise ContractError(
            f"method {row['methodIndex']} {access['jobField']} has an out-of-span instruction offset"
        )

    observed = [
        _memory_instruction(body, offset)
        for offset in offsets
    ]
    imuls = [entry["immediate"] for entry in observed if entry and entry.get("kind") == "imul"]
    memories = [entry for entry in observed if entry and entry.get("kind") == "memory"]
    if imuls:
        actual_stride = imuls[0]
        if any(value != actual_stride for value in imuls):
            raise ContractError(f"method {row['methodIndex']} {access['jobField']} has inconsistent imul strides")
    elif memories:
        actual_stride = max(
            int(entry["displacement"]) + int(entry["width"])
            for entry in memories
        )
    else:
        raise ContractError(
            f"method {row['methodIndex']} {access['jobField']} instruction offsets do not decode to memory arithmetic"
        )

    if actual_stride != int(access["strideBytes"]):
        raise ContractError(
            f"method {row['methodIndex']} {access['jobField']} stride drift: "
            f"{actual_stride} != {access['strideBytes']}"
        )
    actual_displacements = sorted({
        int(entry["displacement"])
        for entry in memories
    })
    expected_displacements = sorted(int(value) for value in access["elementFieldDisplacements"])
    # Some array headers are represented only by their index multiply/add; a
    # zero-field entry is still valid when the body has no element load at the
    # selected arithmetic offsets.
    if actual_displacements and actual_displacements != expected_displacements:
        raise ContractError(
            f"method {row['methodIndex']} {access['jobField']} element displacement drift: "
            f"{actual_displacements} != {expected_displacements}"
        )

    # The job-field pointer is read from the outer job payload.  Prove that
    # the recorded offset occurs in an actual rdi/r15/rbx-based instruction;
    # this prevents a copied C# field offset from silently becoming the only
    # evidence for a buffer row.
    job_offset = int(str(access["jobOffset"]), 16)
    found_job_field = False
    for offset in range(span):
        entry = _memory_instruction(body, offset)
        if not entry or entry.get("kind") != "memory":
            continue
        if entry.get("base") in {"rdi", "r15", "rbx"} and int(entry["displacement"]) == job_offset:
            found_job_field = True
            break
    if not found_job_field:
        raise ContractError(
            f"method {row['methodIndex']} {access['jobField']} job offset 0x{job_offset:x} "
            "was not observed in the pinned body"
        )


def _verify_targets(gameassembly: Path, metadata: Path) -> None:
    native, md, pe, method_by_pointer, all_pointers = _native_indexes(metadata, gameassembly)
    signatures_by_index: dict[int, tuple[int, dict[str, Any]]] = {}
    for row in TARGETS:
        method_index = int(row["methodIndex"])
        matches = _register_method_rows(method_by_pointer, method_index)
        if len(matches) != 1:
            raise ContractError(f"method {method_index} resolves to {len(matches)} native pointers")
        pointer, signature = matches[0]
        signatures_by_index[method_index] = (pointer, signature)
        expected_va = int(row["va"], 16)
        if pointer != expected_va:
            raise ContractError(
                f"method {method_index} VA drift: {_hex(pointer)} != {_hex(expected_va)}"
            )
        if signature.get("type") != row["type"] or not _method_label_matches(md, method_index, row["method"]):
            raise ContractError(
                f"method {method_index} identity drift: "
                f"{signature.get('type')}.{signature.get('method')} != {row['type']}.{row['method']}"
            )
        next_index = bisect_right(all_pointers, pointer)
        if next_index >= len(all_pointers):
            raise ContractError(f"method {method_index} has no bounded next native method pointer")
        expected_end = int(row["endVaExclusive"], 16)
        if all_pointers[next_index] != expected_end:
            raise ContractError(
                f"method {method_index} span end drift: {_hex(all_pointers[next_index])} != {_hex(expected_end)}"
            )
        size = int(row["spanBytes"])
        if size != expected_end - expected_va or size <= 0:
            raise ContractError(f"method {method_index} has invalid function span {size}")
        body = pe.bytes_at_va(expected_va, size)
        if len(body) != size:
            raise ContractError(f"method {method_index} span is truncated at {row['va']}")
        actual = hashlib.sha256(body).hexdigest()
        if actual != row["bodySha256"]:
            raise ContractError(
                f"method {method_index} hash drift: {actual[:16]} != {row['bodySha256'][:16]}"
            )
        calls, _unresolved = native.scan_direct_calls(
            pe, expected_va, size, method_by_pointer, set(), include_unresolved=True, arg_context_window=0
        )
        direct_targets = {int(call["targetVa"], 16): call for call in calls}
        for callee in row.get("nextCalls", []):
            callee_index = int(callee["methodIndex"])
            callee_match = signatures_by_index.get(callee_index)
            if callee_match is None:
                callee_rows = _register_method_rows(method_by_pointer, callee_index)
                if len(callee_rows) != 1:
                    raise ContractError(f"callee {callee_index} does not resolve to one native pointer")
                callee_match = callee_rows[0]
            callee_pointer, callee_signature = callee_match
            if callee_pointer != int(callee["va"], 16):
                raise ContractError(f"callee {callee_index} VA does not match method index mapping")
            if not _method_label_matches(md, callee_index, callee["method"]):
                raise ContractError(f"callee {callee_index} name does not match metadata")
            instruction_offsets = callee.get("instructionOffsets") or []
            if not instruction_offsets:
                continue
            actual_offsets = {
                int(call["offset"])
                for call in calls
                if int(call.get("targetVa", "0"), 16) == callee_pointer
            }
            missing = [value for value in instruction_offsets if int(value, 16) not in actual_offsets]
            if missing:
                raise ContractError(
                    f"method {method_index} -> {callee_index} call offsets unresolved: {missing}"
                )
        for access in row.get("bufferAccesses", []):
            _verify_buffer_access(pe, row, access)


def build_contract(
    gameassembly: Path | None = DEFAULT_GAME_ASSEMBLY,
    metadata: Path | None = DEFAULT_METADATA,
) -> dict[str, Any]:
    evidence = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if evidence.status != "validated":
        raise ContractError(f"native evidence gate {evidence.status}: {evidence.detail}")
    _verify_targets(evidence.gameassembly, evidence.metadata)
    return {
        "schema": "endfield.charinfo.secondary-dynamics-solver-static.v1",
        "status": "native_spans_hash_pinned",
        "solverStatus": "managed_fallback_accesses_closed_burst_solver_unresolved",
        "nativeGate": {
            "gameAssembly": {"path": str(evidence.gameassembly), "size": evidence.gameassembly.stat().st_size, "sha256": evidence.gameassembly_sha256},
            "globalMetadata": {"path": str(evidence.metadata), "size": evidence.metadata.stat().st_size, "sha256": evidence.metadata_sha256},
        },
        "boundary": "NativeArray slots are outer job payload pointers; no NativeArray length field is read by indexed managed Execute bodies. _indexCount is read only by Execute() wrappers.",
        "targets": TARGETS,
    }


def _markdown(contract: dict[str, Any]) -> str:
    lines = ["# Secondary dynamics solver static boundary", "", f"Status: `{contract['status']}`.", "", contract["solverStatus"], "", "| Method | Role | Span | Solver classification | Next callee |", "|---|---|---:|---|---|"]
    for row in contract["targets"]:
        calls = ", ".join(f"{x['methodIndex']} `{x['va']}`" for x in row["nextCalls"]) or "-"
        lines.append(f"| {row['methodIndex']} {row['method']} | {row['role']} | `{row['va']}..{row['endVaExclusive']}` ({row['spanBytes']} B) | {row['solverStatus']} | {calls} |")
    lines += ["", "The indexed managed Execute bodies are the only rows with observed element arithmetic. Strides and element field displacements are evidence from the pinned x64 body; Burst range wrappers are not solver implementations.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify checked-in JSON and Markdown match current pinned evidence without writing",
    )
    args = parser.parse_args()
    try:
        contract = build_contract(args.gameassembly, args.metadata)
    except ContractError as exc:
        print(f"[secondary-dynamics-static] {exc}", file=sys.stderr)
        return 2
    if args.check:
        if not args.output.is_file() or not args.markdown.is_file():
            print("[secondary-dynamics-static] checked-in output is missing", file=sys.stderr)
            return 2
        checked_json = json.loads(args.output.read_text(encoding="utf-8"))
        checked_markdown = args.markdown.read_text(encoding="utf-8")
        if checked_json != contract:
            print("[secondary-dynamics-static] JSON output is stale", file=sys.stderr)
            return 2
        if checked_markdown != _markdown(contract):
            print("[secondary-dynamics-static] Markdown output is stale", file=sys.stderr)
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
