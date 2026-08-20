#!/usr/bin/env python3
"""Build a fail-closed static contract for Spring (method 385698).

The contract is intentionally narrower than a solver implementation.  It
closes the selected client's exact method span/hash, direct call sites,
conditional branch targets, RIP-relative constants, and the value/job fields
whose memory operands are visible in the managed helper.  It does not execute
the helper, reconstruct Burst's range kernel, or claim transform equivalence.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_spring_semantics_contract.json"
DEFAULT_MARKDOWN = SOURCE_ROOT / "secondary_dynamics_spring_semantics_contract.md"
STATIC_CONTRACT = SOURCE_ROOT / "secondary_dynamics_solver_static_contract.json"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_TYPE = "BeyondDynamicBone.SimulationManager+StartSimulationStepJob"
METHOD_INDEX = 385698
METHOD_VA = 0x186775AE4
METHOD_END = 0x186776080
METHOD_SHA256 = "149382eea39d5d1a3ca0e27ed701a665f51406664766283b070305adc52050b5"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    """Raised when selected-client evidence does not match the contract."""


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _static_module() -> Any:
    return _load("secondary_spring_static", LAB_ROOT / "tools/build_secondary_dynamics_solver_static_contract.py")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _file(path: Path, digest: str | None = None) -> dict[str, Any]:
    return {"path": _repo_path(path), "size": path.stat().st_size,
            "sha256": digest or _sha256(path)}


def _native_gate(gameassembly: Path | None, metadata: Path | None) -> tuple[Path, Path, dict[str, Any]]:
    evidence = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if evidence.status != "validated":
        raise ContractError(f"common.check_installed_native_inputs [{evidence.status}]: {evidence.detail}")
    game_path = Path(evidence.gameassembly)
    metadata_path = Path(evidence.metadata)
    return game_path, metadata_path, {
        "gameAssembly": _file(game_path, evidence.gameassembly_sha256),
        "globalMetadata": _file(metadata_path, evidence.metadata_sha256),
    }


def _signed_i32(pe: Any, va: int) -> int:
    return struct.unpack("<i", struct.pack("<I", pe.u32_at_va(va)))[0]


def _type_record(module: Any, *, md: Any, pe: Any, registration: dict[str, Any],
                 pointer_index: dict[int, list[int]], type_index: int, label: str) -> dict[str, Any]:
    return module._type_record(
        md=md, pe=pe, registration=registration,
        type_pointer_index=pointer_index, metadata_type_index=type_index, label=label,
    )


def _direct_layout(module: Any, *, md: Any, pe: Any, registration: dict[str, Any],
                   pointer_index: dict[int, list[int]], type_index: int) -> dict[str, Any]:
    type_def = md.types[type_index]
    field_table = int(registration["fieldOffsets"], 16)
    field_pointer = pe.u64_at_va(field_table + type_index * 8)
    size_table = int(registration["typeDefinitionsSizes"], 16)
    size_pointer = pe.u64_at_va(size_table + type_index * 8)
    if not field_pointer or not size_pointer:
        raise ContractError(f"{md.type_full_name(type_def)} lacks field/size registration")
    instance_size = pe.u32_at_va(size_pointer)
    native_size = _signed_i32(pe, size_pointer + 4)
    fields: list[dict[str, Any]] = []
    previous = -1
    for index, field in enumerate(md.fields_for(type_def)):
        boxed = _signed_i32(pe, field_pointer + index * 4)
        native_offset = boxed - 16
        if native_offset < previous:
            raise ContractError(f"{md.type_full_name(type_def)} fields overlap")
        fields.append({
            "name": md.string(field.name_index),
            "metadataTypeIndex": field.type_index,
            "metadataType": _type_record(
                module, md=md, pe=pe, registration=registration,
                pointer_index=pointer_index, type_index=field.type_index,
                label=f"{md.type_full_name(type_def)} field",
            ),
            "boxedFieldOffset": f"0x{boxed:x}",
            "nativePayloadOffset": f"0x{native_offset:x}",
            "token": f"0x{field.token:08x}",
        })
        previous = native_offset
    if instance_size != native_size + 16:
        raise ContractError(f"{md.type_full_name(type_def)} size relation drift")
    return {
        "name": md.type_full_name(type_def),
        "typeDefinitionIndex": type_index,
        "fieldStart": type_def.field_start,
        "fieldCount": type_def.field_count,
        "instanceSizeBytes": instance_size,
        "nativeSizeBytes": native_size,
        "directFieldsOnly": True,
        "fields": fields,
    }


# These are the direct call sites observed in the fixed method span.  The
# target VAs are deliberately kept as addresses, not guessed managed names;
# many are generic Unity.Mathematics bodies that do not have a unique IL2CPP
# method-pointer row.
CALL_TARGETS: tuple[tuple[int, int], ...] = (
    (0x52, 0x180035ED0), (0x69, 0x182F95A30), (0xB1, 0x185F00F40),
    (0xEA, 0x18415F9A0), (0x138, 0x183F48480), (0x19A, 0x18415F9A0),
    (0x1CD, 0x186689AFC), (0x213, 0x18415F9A0), (0x244, 0x185F0AE78),
    (0x249, 0x1801D32D0), (0x27B, 0x185F00ED4), (0x2BD, 0x185F0AE78),
    (0x2E3, 0x185F00ED4), (0x315, 0x185F00F40), (0x341, 0x185F0AE78),
    (0x346, 0x1801D32D0), (0x353, 0x1801D7EA0), (0x358, 0x1801D8880),
    (0x3BB, 0x185F00ED4), (0x3D5, 0x185F355BC), (0x3E6, 0x185F00ED4),
    (0x418, 0x185F00F40), (0x43D, 0x1801D9D00), (0x486, 0x185F00ED4),
    (0x4B8, 0x185F00F40), (0x4F2, 0x185F00D7C), (0x510, 0x185396738),
    (0x51D, 0x1800D8260), (0x55F, 0x1866E13D0),
)

# Both conditional and unconditional control-flow edges are included.  The
# condition is a native instruction property; the selected runtime outcome is
# intentionally not inferred.
BRANCH_TARGETS: tuple[tuple[int, str, int], ...] = (
    (0x49, "jne", 0x5E), (0x70, "jne", 0x50B),
    (0xF9, "je", 0x17F), (0x102, "je", 0x171),
    (0x107, "je", 0x166), (0x10C, "je", 0x15E),
    (0x111, "je", 0x150), (0x116, "jne", 0x1A7),
    (0x14E, "jmp", 0x191), (0x15C, "jmp", 0x128),
    (0x164, "jmp", 0x156), (0x16F, "jmp", 0x188),
    (0x17D, "jmp", 0x18B), (0x1E9, "ja", 0x21D),
    (0x218, "jmp", 0x41D), (0x256, "jbe", 0x28A),
    (0x28E, "jbe", 0x427), (0x389, "jbe", 0x427),
    (0x436, "jbe", 0x46E), (0x469, "ja", 0x46E),
    (0x509, "jmp", 0x564), (0x51B, "jne", 0x523),
)

# RIP-relative constants are read from executable instructions.  The values
# are stored in the generated JSON along with raw instruction bytes and source
# addresses so a future build cannot silently re-use a nearby literal.
CONSTANT_TARGETS: tuple[tuple[int, int, str, int], ...] = (
    (0xB6, 0x18B959200, "float32", 4),
    (0x1E1, 0x18B9593B4, "float32", 4),
    (0x447, 0x18B959530, "float32", 4),
    (0x45E, 0x18B959248, "float64", 8),
)
CONSTANT_INSTRUCTION_BYTES = {
    0xB6: "f30f103d5e361e05",
    0x1E1: "440f2f05e7361e05",
    0x447: "f30f590dfd351e05",
    0x45E: "660f2f05fe321e05",
}

# Memory sites are declared with the semantic owner derived from the job and
# method signatures.  The verifier decodes the base register, displacement and
# width from the native instruction, then checks these values exactly.
MEMORY_SITES: tuple[tuple[int, str, str, int, int, str], ...] = (
    (0x88, "basePos", "r15", 0x0, 16, "read"),
    (0x8C, "basePos", "r15", 0x10, 8, "read"),
    (0x97, "nextPos", "r14", 0x0, 16, "read"),
    (0xA0, "nextPos", "r14", 0x10, 8, "read"),
    (0x1DB, "SpringConstraintParams.limitDistance", "rdi", 0x4, 4, "read"),
    (0x258, "job.simulationDeltaTime", "rsi", 0x10, 8, "read"),
    (0x262, "job.simulationPower", "rsi", 0x0, 16, "read"),
    (0x28A, "SpringConstraintParams.normalLimitRatio", "rdi", 0x8, 4, "read"),
    (0x35D, "SpringConstraintParams.normalLimitRatio", "rdi", 0x8, 4, "read"),
    (0x427, "SpringConstraintParams.springNoise", "rdi", 0xC, 4, "read"),
    (0x42F, "SpringConstraintParams.springPower", "rdi", 0x0, 4, "read"),
    (0x442, "SpringConstraintParams.springNoise", "rdi", 0xC, 4, "read"),
    (0x4D8, "basePos", "r15", 0x0, 16, "read"),
    (0x4E1, "basePos", "r15", 0x10, 8, "read"),
    (0x4FF, "nextPos", "r14", 0x0, 16, "write"),
    (0x503, "nextPos", "r14", 0x10, 8, "write"),
)

ABI_SITES: tuple[tuple[int, str, str, str], ...] = (
    (0x26, "nextPos", "r14", "4d8bf1"),
    (0x2D, "normalAxis", "ebx", "418bd8"),
    (0x34, "springParams", "rdi", "488bfa"),
    (0x3C, "this/job", "rsi", "488bf1"),
    (0x76, "basePos", "r15", "4c8b7d50"),
    (0x1A7, "baseRot", "[rbp+0x58]", "488b4558"),
    (0x1D2, "scaleRatio", "[rbp+0x68]", "f3440f104568"),
    (0x438, "noiseTime", "[rbp+0x60]", "f20f104560"),
)


def _reg_name(code: int) -> str:
    names = ("rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
             "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15")
    return names[code]


def _decode_memory(data: bytes, offset: int) -> dict[str, Any]:
    """Decode the bounded ModRM memory subset used by Spring sites."""
    pos = offset
    prefixes: list[int] = []
    while pos < len(data) and data[pos] in (0x66, 0xF2, 0xF3):
        prefixes.append(data[pos]); pos += 1
    rex = 0
    if pos < len(data) and 0x40 <= data[pos] <= 0x4F:
        rex = data[pos]; pos += 1
    if pos >= len(data):
        raise ContractError(f"memory site 0x{offset:x} is truncated")
    opcode = data[pos]; pos += 1
    opcode2: int | None = None
    if opcode == 0x0F:
        if pos >= len(data):
            raise ContractError(f"memory site 0x{offset:x} lacks second opcode")
        opcode2 = data[pos]; pos += 1
    width_table = {
        (0x0F, 0x10): 4 if 0xF3 in prefixes else 8 if 0xF2 in prefixes else 16,
        (0x0F, 0x11): 4 if 0xF3 in prefixes else 8 if 0xF2 in prefixes else 16,
        (0x0F, 0x2F): 8 if 0xF2 in prefixes else 4,
        (0x0F, 0x59): 4,
    }
    width = width_table.get((opcode, opcode2))
    if width is None:
        raise ContractError(f"memory site 0x{offset:x} has unsupported opcode")
    if pos >= len(data):
        raise ContractError(f"memory site 0x{offset:x} lacks ModRM")
    modrm = data[pos]; pos += 1
    mod, rm = (modrm >> 6) & 3, modrm & 7
    if mod == 3:
        raise ContractError(f"memory site 0x{offset:x} is not a memory operand")
    rex_b = rex & 1
    base = rm | (rex_b << 3)
    if rm == 4:
        if pos >= len(data):
            raise ContractError(f"memory site 0x{offset:x} lacks SIB")
        sib = data[pos]; pos += 1
        raw_base = sib & 7
        base = raw_base | (rex_b << 3)
        if mod == 0 and raw_base == 5:
            base = -1
    if mod == 0:
        displacement = 0
        if rm == 5 or (rm == 4 and base == -1):
            displacement = struct.unpack_from("<i", data, pos)[0]; pos += 4
    elif mod == 1:
        displacement = struct.unpack_from("<b", data, pos)[0]; pos += 1
    elif mod == 2:
        displacement = struct.unpack_from("<i", data, pos)[0]; pos += 4
    else:
        displacement = 0
    direction = "write" if opcode == 0x0F and opcode2 == 0x11 else "read"
    return {"base": None if base < 0 else _reg_name(base),
            "displacement": displacement, "widthBytes": width,
            "direction": direction,
            "instructionBytes": data[offset:pos].hex()}


def _branch_bytes(body: bytes, offset: int) -> tuple[str, int, str]:
    if offset >= len(body):
        raise ContractError(f"branch offset 0x{offset:x} is outside Spring")
    first = body[offset]
    if first == 0x0F:
        if offset + 6 > len(body) or not 0x80 <= body[offset + 1] <= 0x8F:
            raise ContractError(f"invalid near branch at 0x{offset:x}")
        displacement = struct.unpack_from("<i", body, offset + 2)[0]
        mnemonic = {0x84: "je", 0x85: "jne", 0x86: "jbe", 0x87: "ja"}.get(body[offset + 1])
        if mnemonic is None:
            raise ContractError(f"unsupported near condition opcode at 0x{offset:x}")
        return (mnemonic, offset + 6 + displacement, body[offset:offset + 6].hex())
    if 0x70 <= first <= 0x7F or first == 0xEB:
        if offset + 2 > len(body):
            raise ContractError(f"invalid short branch at 0x{offset:x}")
        displacement = struct.unpack_from("<b", body, offset + 1)[0]
        if first == 0xEB:
            mnemonic = "jmp"
        else:
            mnemonic = {0x74: "je", 0x75: "jne", 0x76: "jbe", 0x77: "ja"}.get(first)
            if mnemonic is None:
                raise ContractError(f"unsupported short condition opcode at 0x{offset:x}")
        return (mnemonic, offset + 2 + displacement, body[offset:offset + 2].hex())
    if first == 0xE9:
        if offset + 5 > len(body):
            raise ContractError(f"invalid near jmp at 0x{offset:x}")
        displacement = struct.unpack_from("<i", body, offset + 1)[0]
        return ("jmp", offset + 5 + displacement, body[offset:offset + 5].hex())
    raise ContractError(f"unsupported branch opcode at 0x{offset:x}")


def _call_target(body: bytes, offset: int, method_va: int) -> tuple[int, str]:
    if offset + 5 > len(body) or body[offset] != 0xE8:
        raise ContractError(f"direct call at 0x{offset:x} is not E8 rel32")
    displacement = struct.unpack_from("<i", body, offset + 1)[0]
    return method_va + offset + 5 + displacement, body[offset:offset + 5].hex()


def _constant_site(body: bytes, method_va: int, offset: int, expected_target: int,
                   value_kind: str, width: int) -> dict[str, Any]:
    if offset + 8 > len(body):
        raise ContractError(f"constant site 0x{offset:x} is truncated")
    # All selected sites are an eight-byte RIP-relative SSE instruction.
    displacement = struct.unpack_from("<i", body, offset + 4)[0]
    actual_target = method_va + offset + 8 + displacement
    if actual_target != expected_target:
        raise ContractError(
            f"constant site 0x{offset:x} target drift: 0x{actual_target:x} != 0x{expected_target:x}"
        )
    raw = body[offset:offset + 8]
    expected_bytes = CONSTANT_INSTRUCTION_BYTES[offset]
    if raw.hex() != expected_bytes:
        raise ContractError(
            f"constant site 0x{offset:x} opcode/prefix/ModRM drift: "
            f"actual={raw.hex()} expected={expected_bytes}"
        )
    if value_kind == "float32":
        value = struct.unpack("<f", _read_native_bytes(expected_target, width))[0]
    else:
        value = struct.unpack("<d", _read_native_bytes(expected_target, width))[0]
    return {"instructionOffset": f"0x{offset:x}", "targetVa": f"0x{expected_target:x}",
            "valueKind": value_kind, "widthBytes": width, "value": value,
            "instructionBytes": raw.hex()}


_ACTIVE_PE: Any = None


def _read_native_bytes(va: int, size: int) -> bytes:
    if _ACTIVE_PE is None:
        raise ContractError("native image is not active")
    return _ACTIVE_PE.bytes_at_va(va, size)


def _verify_memory_sites(body: bytes) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for offset, owner, register, displacement, width, access in MEMORY_SITES:
        decoded = _decode_memory(body, offset)
        if (decoded["base"] != register or decoded["displacement"] != displacement
                or decoded["widthBytes"] != width or decoded["direction"] != access):
            raise ContractError(
                f"memory site 0x{offset:x} drift: actual={decoded} expected="
                f"{register}+0x{displacement:x}/{width}/{access}"
            )
        result.append({
            "instructionOffset": f"0x{offset:x}", "owner": owner,
            "baseRegister": register, "displacementBytes": displacement,
            "widthBytes": width, "access": access,
            "instructionBytes": decoded["instructionBytes"],
        })
    return result


def _verify_abi_sites(body: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for offset, argument, location, expected_hex in ABI_SITES:
        actual = body[offset:offset + len(bytes.fromhex(expected_hex))].hex()
        if actual != expected_hex:
            raise ContractError(
                f"Spring ABI site 0x{offset:x} drift: {actual} != {expected_hex}"
            )
        rows.append({"instructionOffset": f"0x{offset:x}", "argument": argument,
                     "location": location, "instructionBytes": actual})
    return rows


def _verify_method(static: Any, gameassembly: Path, metadata: Path, static_contract: dict[str, Any]) -> dict[str, Any]:
    global _ACTIVE_PE
    native, md, pe, method_by_pointer, all_pointers = static._native_indexes(metadata, gameassembly)
    _ACTIVE_PE = pe
    rows = static._register_method_rows(method_by_pointer, METHOD_INDEX)
    if len(rows) != 1:
        raise ContractError(f"method {METHOD_INDEX} resolves to {len(rows)} native pointers")
    pointer, signature = rows[0]
    if pointer != METHOD_VA:
        raise ContractError(f"method {METHOD_INDEX} VA drift: 0x{pointer:x} != 0x{METHOD_VA:x}")
    if signature.get("type") != EXPECTED_TYPE or not static._method_label_matches(md, METHOD_INDEX, "Spring"):
        raise ContractError("Spring metadata identity drift")
    next_index = bisect.bisect_right(all_pointers, pointer)
    if next_index >= len(all_pointers) or all_pointers[next_index] != METHOD_END:
        raise ContractError("Spring next-method span boundary drift")
    body = pe.bytes_at_va(METHOD_VA, METHOD_END - METHOD_VA)
    actual_sha = hashlib.sha256(body).hexdigest()
    if actual_sha != METHOD_SHA256:
        raise ContractError(f"Spring body hash drift: {actual_sha} != {METHOD_SHA256}")

    expected_static = next(row for row in static_contract["targets"] if int(row["methodIndex"]) == METHOD_INDEX)
    if expected_static["bodySha256"] != actual_sha or int(expected_static["endVaExclusive"], 16) != METHOD_END:
        raise ContractError("static solver contract Spring row is stale")

    calls: list[dict[str, Any]] = []
    for offset, target in CALL_TARGETS:
        actual_target, instruction_bytes = _call_target(body, offset, METHOD_VA)
        if actual_target != target:
            raise ContractError(f"Spring call 0x{offset:x} target drift: 0x{actual_target:x} != 0x{target:x}")
        calls.append({"instructionOffset": f"0x{offset:x}", "targetVa": f"0x{target:x}",
                      "instructionBytes": instruction_bytes})

    branches: list[dict[str, Any]] = []
    for offset, mnemonic, target_offset in BRANCH_TARGETS:
        decoded_mnemonic, actual_target, instruction_bytes = _branch_bytes(body, offset)
        if actual_target != target_offset:
            raise ContractError(f"Spring branch 0x{offset:x} target drift")
        if decoded_mnemonic != mnemonic:
            raise ContractError(
                f"Spring branch 0x{offset:x} condition drift: "
                f"actual={decoded_mnemonic} expected={mnemonic}"
            )
        branches.append({"instructionOffset": f"0x{offset:x}", "mnemonic": mnemonic,
                         "targetOffset": f"0x{target_offset:x}", "instructionBytes": instruction_bytes})

    constants = [
        _constant_site(body, METHOD_VA, offset, target, kind, width)
        for offset, target, kind, width in CONSTANT_TARGETS
    ]
    argument_abi = _verify_abi_sites(body)
    accesses = _verify_memory_sites(body)

    registration = native.metadata_registration_summary(pe, 0x18B921C30)
    element_module = _load(
        "secondary_spring_element",
        LAB_ROOT / "tools/build_secondary_dynamics_element_layout_contract.py",
    )
    pointer_index = element_module._build_type_pointer_index(pe, registration)
    spring_params_layout = _direct_layout(
        element_module,
        md=md, pe=pe, registration=registration, pointer_index=pointer_index, type_index=48138,
    )
    spring_method = md.methods[METHOD_INDEX]
    params = []
    for parameter in md.parameters_for(spring_method):
        params.append({
            "name": md.string(parameter.name_index),
            "metadataTypeIndex": parameter.type_index,
            "metadataType": _type_record(
                element_module,
                md=md, pe=pe, registration=registration, pointer_index=pointer_index,
                type_index=parameter.type_index, label=f"Spring.{md.string(parameter.name_index)}",
            ),
        })
    return {
        "methodIndex": METHOD_INDEX, "type": EXPECTED_TYPE, "method": "Spring",
        "role": "managed_value_helper", "solverStatus": "helper_static_boundary_only",
        "va": f"0x{METHOD_VA:x}", "endVaExclusive": f"0x{METHOD_END:x}",
        "spanBytes": METHOD_END - METHOD_VA, "bodySha256": actual_sha,
        "parameters": params,
        "argumentAbi": argument_abi,
        "directCalls": calls, "branches": branches, "constants": constants,
        "memoryAccesses": accesses,
        "memoryAccessCensus": {
            "status": "bounded_related_operands_closed",
            "registerBasedValueAndJobSites": len(accesses),
            "stackArgumentSites": [row for row in argument_abi if row["location"].startswith("[rbp+")],
            "ripRelativeConstantSites": len(constants),
            "unclassifiedBoundary": (
                "Prologue/epilogue spills, stack temporaries, runtime metadata flags, and "
                "helper-internal scratch addresses are not semantic value/job accesses; "
                "they remain bounded by the pinned body hash and are not promoted to fields."
            ),
        },
        "nativeArrayAccesses": [],
        "arrayStrideStatus": "not_applicable_helper_has_no_nativearray_operand",
        "valueTypeLayouts": [spring_params_layout],
    }


def build_contract(gameassembly: Path | None = DEFAULT_GAME_ASSEMBLY,
                   metadata: Path | None = DEFAULT_METADATA) -> dict[str, Any]:
    game_path, metadata_path, gate = _native_gate(gameassembly, metadata)
    static = _static_module()
    static_contract = static.build_contract(gameassembly=game_path, metadata=metadata_path)
    if not STATIC_CONTRACT.is_file():
        raise ContractError(f"checked-in static solver contract is missing: {STATIC_CONTRACT}")
    checked_static = json.loads(STATIC_CONTRACT.read_text(encoding="utf-8"))
    if checked_static != static_contract:
        raise ContractError("checked-in static solver contract is stale")
    spring = _verify_method(static, game_path, metadata_path, static_contract)
    return {
        "schema": "endfield.charinfo.secondary-dynamics-spring-semantics.v1",
        "status": "managed_spring_static_semantics_closed",
        "solverImplemented": False,
        "retailEquivalent": False,
        "nativeGate": gate,
        "sourceContracts": {"solverStatic": _file(STATIC_CONTRACT, _sha256(STATIC_CONTRACT))},
        "method": spring,
        "boundary": (
            "385698 is the managed Spring helper called by the indexed Execute fallback. "
            "This contract closes native bytes, value/job memory operands, branch targets, "
            "and direct calls only; Burst range execution, runtime patch selection, solver "
            "scheduling, and transform writeback equivalence remain unresolved."
        ),
    }


def _markdown(contract: dict[str, Any]) -> str:
    method = contract["method"]
    lines = [
        "# Secondary dynamics Spring static semantics", "",
        f"Status: `{contract['status']}`.", "",
        f"Method 385698 spans `{method['va']}..{method['endVaExclusive']}` ({method['spanBytes']} bytes) with body hash `{method['bodySha256']}`.",
        "", "This is a managed helper boundary, not a solver or Burst-equivalence claim.", "",
        "| Evidence | Count |", "|---|---:|",
        f"| direct calls | {len(method['directCalls'])} |",
        f"| branch edges | {len(method['branches'])} |",
        f"| RIP constants | {len(method['constants'])} |",
        f"| memory sites | {len(method['memoryAccesses'])} |",
        "",
        "The helper reads `simulationPower`/`simulationDeltaTime`, four direct `SpringConstraintParams` fields, `double3`/`quaternion` value arguments, and writes `nextPos`; it has no NativeArray operand or recoverable array stride.",
        "",
        "The IFix patch gate and fallback call are preserved as native control-flow evidence. Runtime patch state, Burst execution, scheduling, and transform fidelity remain open.",
        "",
    ]
    return "\n".join(lines)


def _first_diff(expected: Any, actual: Any, path: str = "$") -> tuple[str, str, str] | None:
    if type(expected) is not type(actual):
        return path, type(expected).__name__, type(actual).__name__
    if isinstance(expected, dict):
        for key in sorted(set(expected) | set(actual)):
            child = f"{path}.{key}"
            if key not in expected:
                return child, "<missing>", repr(actual[key])[:240]
            if key not in actual:
                return child, repr(expected[key])[:240], "<missing>"
            found = _first_diff(expected[key], actual[key], child)
            if found is not None:
                return found
        return None
    if isinstance(expected, list):
        for index, (left, right) in enumerate(zip(expected, actual)):
            found = _first_diff(left, right, f"{path}[{index}]")
            if found is not None:
                return found
        if len(expected) != len(actual):
            return f"{path}.length", str(len(expected)), str(len(actual))
        return None
    if expected != actual:
        return path, repr(expected)[:240], repr(actual)[:240]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--check", action="store_true", help="verify checked-in outputs without writing")
    args = parser.parse_args()
    try:
        contract = build_contract(args.gameassembly, args.metadata)
    except (ContractError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"[secondary-dynamics-spring] source={args.output} {exc}", file=sys.stderr)
        return 2
    if args.check:
        if not args.output.is_file() or not args.markdown.is_file():
            print("[secondary-dynamics-spring] checked-in output is missing", file=sys.stderr)
            return 2
        checked_json = json.loads(args.output.read_text(encoding="utf-8"))
        difference = _first_diff(contract, checked_json)
        if difference is not None:
            path, expected, actual = difference
            print(
                f"[secondary-dynamics-spring] JSON output is stale: source={args.output} "
                f"path={path} expected={expected} actual={actual}",
                file=sys.stderr,
            )
            return 2
        expected_markdown = _markdown(contract)
        actual_markdown = args.markdown.read_text(encoding="utf-8")
        if actual_markdown != expected_markdown:
            print(
                f"[secondary-dynamics-spring] Markdown output is stale: source={args.markdown} "
                f"expected_sha256={hashlib.sha256(expected_markdown.encode()).hexdigest()} "
                f"actual_sha256={hashlib.sha256(actual_markdown.encode()).hexdigest()}",
                file=sys.stderr,
            )
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
