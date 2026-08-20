#!/usr/bin/env python3
"""Recover the static semantic fingerprint of the Collider Start Burst exports.

The generated Burst DLL exposes several opaque 32-hex exports with the same
outer x64 ABI.  This contract follows each candidate's static function-pointer
slot through the fixed DLL's CPU-variant initializer and into the implementation
body.  It compares the decoded argument order and the first collider/TeamData
accesses with the canonical 17-parameter
``ColliderManager.StartSimulationStepRangeKernel`` signature and the managed
fallback's observed buffer accesses.

This is deliberately *not* a runtime wrapper-to-hash mapping.  The
``BurstDirectCall`` path still resolves through the late-bound Burst compiler
service.  A unique semantic export candidate is useful for subsequent runtime
telemetry, but this report never claims that method 385416 selected that hash.
All native facts are gated by the exact GameAssembly.dll, global-metadata.dat,
and lib_burst_generated.dll hashes for one installed client.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64, x86_const
except ImportError as exc:  # pragma: no cover - environment gate
    Cs = None  # type: ignore[assignment]
    x86_const = None  # type: ignore[assignment]
    _CAPSTONE_IMPORT_ERROR = exc
else:
    _CAPSTONE_IMPORT_ERROR = None


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_collider_start_semantics_contract.json"
DEFAULT_MARKDOWN = SOURCE_ROOT / "secondary_dynamics_collider_start_semantics_contract.md"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_LIB_BURST_SHA256 = "ee8702dd63dec2db7dc29d5bc23b8acd032f0e19a0daad5f69e6c45f9d3ceb99"
EXPECTED_BURST_EXPORT_COUNT = 628

BURST_EXPORT_BUILDER = LAB_ROOT / "tools/build_secondary_dynamics_burst_export_contract.py"
SOLVER_STATIC_PATH = SOURCE_ROOT / "secondary_dynamics_solver_static_contract.json"
BURST_EXPORT_JSON = SOURCE_ROOT / "secondary_dynamics_burst_export_contract.json"

CANONICAL_PARAMETERS = [
    "jobColliderIndexList",
    "teamDataArray",
    "centerDataArray",
    "teamIdArray",
    "flagArray",
    "sizeArray",
    "framePositions",
    "frameRotations",
    "frameScales",
    "oldFramePositions",
    "oldFrameRotations",
    "nowPositions",
    "nowRotations",
    "oldPositions",
    "oldRotations",
    "workDataArray",
    # The generated BurstDirectCall metadata calls this NativeArray<int>
    # parameter ``lengthPtr``.  Its managed range-kernel role is the Execute
    # index; retain the metadata name and record that role separately.
    "lengthPtr",
]

EXPECTED_CANDIDATE_HASHES = {
    "4aa6773b1eaf6055e0feb9593e092585",
    "7342567c29c434b5b924be51bd8e34b7",
    "8b3d2761aaaac71a35d4a2557d570456",
}

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class ContractError(RuntimeError):
    """Raised when fixed-client evidence no longer closes."""


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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
        return path.resolve().as_posix()


def _file(path: Path, digest: str | None = None) -> dict[str, Any]:
    return {"path": _path(path), "size": path.stat().st_size,
            "sha256": digest or _sha256(path)}


def _native_gate(game_assembly: Path | None, metadata: Path | None) -> dict[str, Any]:
    from scripts.common import check_installed_native_inputs

    result = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=game_assembly,
        metadata=metadata,
    )
    if not result.validated:
        raise ContractError(
            f"common.check_installed_native_inputs [{result.status}]: {result.detail}"
        )
    ga = Path(result.gameassembly)
    md = Path(result.metadata)
    burst = ga.parent / "Endfield_Data/Plugins/x86_64/lib_burst_generated.dll"
    if not burst.is_file():
        raise ContractError(f"missing pinned lib_burst_generated.dll: {burst}")
    burst_sha = _sha256(burst)
    if burst_sha != EXPECTED_LIB_BURST_SHA256:
        raise ContractError(f"lib_burst_generated.dll sha256 mismatch: {burst_sha}")
    return {
        "gameAssembly": _file(ga, result.gameassembly_sha256),
        "globalMetadata": _file(md, result.metadata_sha256),
        "libBurstGenerated": _file(burst, burst_sha),
    }


def _load_burst_export_contract(gameassembly: Path, metadata: Path) -> dict[str, Any]:
    del gameassembly, metadata
    if not BURST_EXPORT_JSON.is_file():
        raise ContractError(f"missing Burst export contract: {BURST_EXPORT_JSON}")
    try:
        contract = json.loads(BURST_EXPORT_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ContractError(f"invalid Burst export contract: {exc}") from exc
    target = contract.get("targets", {}).get("colliderStartRange", {})
    candidates = target.get("candidates", [])
    hashes = {row.get("hash") for row in candidates}
    if hashes != EXPECTED_CANDIDATE_HASHES:
        raise ContractError(
            f"Collider Start candidate set drift: {sorted(hashes)}"
        )
    if target.get("managedMethodIndex") != 385394 or target.get("directInvokeMethodIndex") != 385416:
        raise ContractError("Burst export contract Collider Start method identity drift")
    if contract.get("pe", {}).get("hashedExportCount") != EXPECTED_BURST_EXPORT_COUNT:
        raise ContractError("Burst export contract hashed export cardinality drift")
    gate = contract.get("native_gate", {})
    if gate.get("gameAssembly", {}).get("sha256") != EXPECTED_GAME_ASSEMBLY_SHA256 or gate.get("globalMetadata", {}).get("sha256") != EXPECTED_METADATA_SHA256 or gate.get("libBurstGenerated", {}).get("sha256") != EXPECTED_LIB_BURST_SHA256:
        raise ContractError("Burst export contract native gate drift")
    rows = {row["hash"]: row for row in contract.get("exports", [])}
    if not EXPECTED_CANDIDATE_HASHES <= rows.keys():
        raise ContractError("Burst export contract omits a candidate export row")
    return {"contract": contract, "rows": {key: rows[key] for key in EXPECTED_CANDIDATE_HASHES}}


def _validate_solver_fallback() -> dict[str, Any]:
    if not SOLVER_STATIC_PATH.is_file():
        raise ContractError(f"missing solver static contract: {SOLVER_STATIC_PATH}")
    try:
        payload = json.loads(SOLVER_STATIC_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ContractError(f"invalid solver static contract: {exc}") from exc
    row = next((item for item in payload.get("targets", []) if item.get("methodIndex") == 385451), None)
    if row is None or row.get("role") != "managed_fallback":
        raise ContractError("solver static contract lacks Collider Start managed fallback")
    expected = {
        "jobColliderIndexList": (0x0, 4, [0]),
        "flagArray": (0x40, 1, [0]),
        "teamIdArray": (0x30, 2, [0]),
        "teamDataArray": (0x10, 464, [0, 16, 32, 48, 64, 80, 96, 112]),
        "centerDataArray": (0x20, 696, [0]),
        "framePositions": (0x60, 24, [0, 16]),
        "oldFramePositions": (0x90, 24, [0, 16]),
        "nowPositions": (0xB0, 24, [0, 16]),
        "nowRotations": (0xC0, 16, [0]),
        "oldPositions": (0xD0, 24, [0, 16]),
        "oldRotations": (0xE0, 16, [0]),
        "workDataArray": (0xF0, 184, [0, 16, 32, 48, 64, 80, 96]),
    }
    actual = {}
    for access in row.get("bufferAccesses", []):
        name = access.get("jobField")
        if name not in expected:
            continue
        actual[name] = {
            "jobOffset": int(str(access.get("jobOffset", "0")), 16),
            "strideBytes": access.get("strideBytes"),
            "elementFieldDisplacements": access.get("elementFieldDisplacements", []),
        }
    for name, (offset, stride, displacements) in expected.items():
        got = actual.get(name)
        if got is None:
            raise ContractError(f"managed fallback missing buffer access: {name}")
        if (got["jobOffset"], got["strideBytes"], got["elementFieldDisplacements"]) != (offset, stride, displacements):
            raise ContractError(f"managed fallback access drift for {name}: {got}")
    return {
        "methodIndex": 385451,
        "bodySha256": row.get("bodySha256"),
        "bufferAccesses": actual,
        "source": _file(SOLVER_STATIC_PATH),
    }


def _metadata_parameter_names(metadata: Path) -> dict[str, Any]:
    catalog_path = REPO_ROOT / "tools/endfield-il2cpp/catalog_option_flow_metadata.py"
    catalog = _load_module("secondary_collider_metadata", catalog_path)
    md = catalog.Metadata(metadata)
    method = md.methods[385416]
    names = [md.string(param.name_index) for param in md.parameters_for(method)]
    if names != CANONICAL_PARAMETERS:
        raise ContractError(f"metadata method 385416 parameter names drift: {names}")
    return {
        "methodIndex": 385416,
        "parameterCount": method.parameter_count,
        "parameters": names,
        "parameterTypeIndices": [param.type_index for param in md.parameters_for(method)],
        "metadataSource": _file(metadata),
    }


class PeImage:
    """Minimal PE section/RUNTIME_FUNCTION reader for the pinned Burst DLL."""

    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes()
        if self.data[:2] != b"MZ":
            raise ContractError("lib_burst_generated.dll is not a PE image")
        pe = struct.unpack_from("<I", self.data, 0x3C)[0]
        if self.data[pe:pe + 4] != b"PE\0\0":
            raise ContractError("lib_burst_generated.dll has no PE signature")
        coff = pe + 4
        self.section_count = struct.unpack_from("<H", self.data, coff + 2)[0]
        optional_size = struct.unpack_from("<H", self.data, coff + 16)[0]
        optional = coff + 20
        if struct.unpack_from("<H", self.data, optional)[0] != 0x20B:
            raise ContractError("lib_burst_generated.dll is not PE32+")
        self.image_base = struct.unpack_from("<Q", self.data, optional + 24)[0]
        self.sections: list[tuple[str, int, int, int, int]] = []
        section_table = optional + optional_size
        for index in range(self.section_count):
            row = section_table + index * 40
            name = self.data[row:row + 8].rstrip(b"\0").decode("ascii", errors="replace")
            virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from("<IIII", self.data, row + 8)
            self.sections.append((name, virtual_address, max(virtual_size, raw_size), raw_pointer, raw_size))
        self.runtime_functions = self._runtime_functions(optional)

    def rva_offset(self, rva: int, size: int = 1) -> int:
        for _name, va, span, raw, _raw_size in self.sections:
            if va <= rva and rva + size <= va + span:
                offset = raw + rva - va
                if 0 <= offset <= len(self.data) - size:
                    return offset
        raise ContractError(f"Burst RVA 0x{rva:x} is outside sections")

    def bytes_at_rva(self, rva: int, size: int) -> bytes:
        return self.data[self.rva_offset(rva, size):self.rva_offset(rva, size) + size]

    def _runtime_functions(self, optional: int) -> list[tuple[int, int, int]]:
        exception_rva, exception_size = struct.unpack_from("<II", self.data, optional + 112 + 8 * 3)
        if not exception_rva or exception_size < 12 or exception_size % 12:
            raise ContractError("lib_burst_generated.dll has no valid exception table")
        result = []
        for offset in range(0, exception_size, 12):
            raw = self.rva_offset(exception_rva + offset, 12)
            begin, end, unwind = struct.unpack_from("<III", self.data, raw)
            if begin < end:
                result.append((begin, end, unwind))
        if not result:
            raise ContractError("lib_burst_generated.dll exception table is empty")
        return result

    def function_boundary(self, rva: int) -> tuple[int, int, int]:
        matches = [row for row in self.runtime_functions if row[0] <= rva < row[1]]
        if len(matches) != 1:
            raise ContractError(f"expected one Burst runtime function for 0x{rva:x}, found {len(matches)}")
        return matches[0]


def _decoder() -> Any:
    if Cs is None:
        raise ContractError(f"Capstone unavailable: {_CAPSTONE_IMPORT_ERROR}")
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = True
    return decoder


def _memory_operand(ins: Any, operand: Any, base_name: str | None = None) -> Any | None:
    if operand.type != x86_const.X86_OP_MEM:
        return None
    if base_name is not None and ins.reg_name(operand.mem.base) != base_name:
        return None
    return operand.mem


def _param_from_rbp_disp(displacement: int, *, first_stack_offset: int) -> int | None:
    if displacement == first_stack_offset + 12 * 8:
        return 17
    if displacement < first_stack_offset or displacement > first_stack_offset + 11 * 8:
        return None
    if (displacement - first_stack_offset) % 8:
        return None
    return 5 + (displacement - first_stack_offset) // 8


def _candidate_call_mapping(instructions: list[Any]) -> dict[str, Any]:
    state: dict[str, str] = {"rcx": "param1", "rdx": "param2", "r8": "param3", "r9": "param4"}
    stack_writes: dict[int, str] = {}
    last_call: Any | None = None
    for ins in instructions:
        if ins.mnemonic == "mov" and len(ins.operands) == 2:
            dst, src = ins.operands
            if dst.type == x86_const.X86_OP_REG:
                dst_name = ins.reg_name(dst.reg)
                mem = _memory_operand(ins, src, "rbp")
                if mem is not None:
                    # Burst thunks use rbp+0x70..0xd0; the relation is
                    # derived below from observed first stack source.
                    if mem.disp >= 0x70:
                        state[dst_name] = f"stack+0x{mem.disp:x}"
                    elif src.type == x86_const.X86_OP_REG:
                        state[dst_name] = state.get(ins.reg_name(src.reg), "unknown")
            if dst.type == x86_const.X86_OP_MEM and ins.reg_name(dst.mem.base) == "rsp":
                src_name = ins.reg_name(src.reg) if src.type == x86_const.X86_OP_REG else "unknown"
                stack_writes[dst.mem.disp] = state.get(src_name, "unknown")
        if ins.mnemonic == "call" and ins.operands:
            last_call = ins
    if last_call is None:
        raise ContractError("Collider Start candidate has no internal call")
    # The candidate wrappers all establish rbp=rsp+0x80 and expose the
    # first stack argument at rbp+0x70.  Keep this explicit and fail closed
    # if a future generated thunk uses a different ABI prologue.
    first_stack = 0x70
    def normalize(value: str) -> str:
        if value.startswith("stack+"):
            disp = int(value.split("+", 1)[1], 16)
            param = _param_from_rbp_disp(disp, first_stack_offset=first_stack)
            if param is not None:
                return f"param{param}"
        return value
    stack = {offset: normalize(source) for offset, source in stack_writes.items()}
    args = [normalize(state.get(reg, f"param{index}")) for index, reg in enumerate(("rcx", "rdx", "r8", "r9"), 1)]
    args += [stack.get(offset, "missing") for offset in range(0x20, 0x80, 8)]
    args += [stack.get(0x80, "missing")]
    return {
        "registerSourcesAtCall": args[:4],
        "stackSourcesAtCall": args[4:],
        "callArgumentSources": args,
        "canonicalOrderExact": args == [f"param{index}" for index in range(1, 18)],
        "callInstructionOffset": f"0x{last_call.address - instructions[0].address:x}",
    }


def _find_call_slot(pe: PeImage, row: dict[str, Any]) -> tuple[int, Any, list[Any], bytes]:
    rva = int(row["rva"], 16)
    offset = int(row["fileOffset"], 16)
    code = pe.data[offset:offset + int(row["spanBytes"])]
    decoder = _decoder()
    decoded = list(decoder.disasm(code, pe.image_base + rva))
    ret_index = next((index for index, ins in enumerate(decoded) if ins.mnemonic == "ret"), None)
    if ret_index is None:
        raise ContractError(f"candidate {row['hash']} does not end at a decoded ret")
    instructions = decoded[:ret_index + 1]
    calls = [ins for ins in instructions if ins.mnemonic == "call" and ins.operands]
    indirect = [ins for ins in calls if ins.operands[0].type == x86_const.X86_OP_MEM and ins.operands[0].mem.base == x86_const.X86_REG_RIP]
    if len(indirect) != 1:
        raise ContractError(f"candidate {row['hash']} expected one RIP-indirect call, found {len(indirect)}")
    call = indirect[0]
    slot_va = call.address + call.size + call.operands[0].mem.disp
    slot_rva = slot_va - pe.image_base
    mapping = _candidate_call_mapping(instructions)
    return slot_rva, call, instructions, code


def _slot_assignments(pe: PeImage, slot_rva: int) -> list[dict[str, Any]]:
    decoder = _decoder()
    assignments: list[dict[str, Any]] = []
    text = next((section for section in pe.sections if section[0] == ".text"), None)
    if text is None:
        raise ContractError("Burst DLL has no .text section")
    _name, text_rva, text_span, text_raw, text_raw_size = text
    instructions = list(decoder.disasm(
        pe.data[text_raw:text_raw + text_raw_size],
        pe.image_base + text_rva,
    ))
    for index, ins in enumerate(instructions):
        if ins.mnemonic != "mov" or len(ins.operands) != 2:
            continue
        dst, src = ins.operands
        if dst.type != x86_const.X86_OP_MEM or dst.mem.base != x86_const.X86_REG_RIP:
            continue
        if src.type != x86_const.X86_OP_REG or ins.reg_name(src.reg) != "rax" or dst.size != 8:
            continue
        target = ins.address + ins.size + dst.mem.disp - pe.image_base
        if target != slot_rva:
            continue
        if index == 0:
            raise ContractError(f"slot 0x{slot_rva:x} assignment has no preceding lea")
        previous = instructions[index - 1]
        if previous.mnemonic != "lea" or len(previous.operands) != 2:
            raise ContractError(f"slot 0x{slot_rva:x} assignment is not preceded by lea")
        pdst, psrc = previous.operands
        if pdst.type != x86_const.X86_OP_REG or previous.reg_name(pdst.reg) != "rax" or psrc.type != x86_const.X86_OP_MEM or psrc.mem.base != x86_const.X86_REG_RIP:
            raise ContractError(f"slot 0x{slot_rva:x} preceding instruction is not RIP lea rax")
        entry = previous.address + previous.size + psrc.mem.disp - pe.image_base
        begin, end, unwind = pe.function_boundary(entry)
        body = pe.bytes_at_rva(begin, end - begin)
        entry_instructions = list(decoder.disasm(body, pe.image_base + begin))
        if not entry_instructions:
            raise ContractError(f"Burst implementation entry 0x{entry:x} is undecodable")
        # Burst emits a small ABI wrapper, then a tiny tail-jump trampoline,
        # before the actual generated core. Follow only those bounded wrappers;
        # never chase an arbitrary helper call from a large core.
        chain: list[dict[str, Any]] = []
        current = begin
        tail_target = None
        core = None
        for _depth in range(4):
            current_begin, current_end, current_unwind = pe.function_boundary(current)
            current_body = pe.bytes_at_rva(current_begin, current_end - current_begin)
            current_instructions = list(decoder.disasm(current_body, pe.image_base + current_begin))
            if not current_instructions:
                raise ContractError(f"Burst implementation entry 0x{current:x} is undecodable")
            chain.append({
                "beginRva": f"0x{current_begin:x}",
                "endRvaExclusive": f"0x{current_end:x}",
                "spanBytes": current_end - current_begin,
                "bodySha256": hashlib.sha256(current_body).hexdigest(),
                "unwindInfoRva": f"0x{current_unwind:x}",
            })
            last = current_instructions[-1]
            if last.mnemonic == "jmp" and last.operands and last.operands[0].type == x86_const.X86_OP_IMM:
                tail_target = last.operands[0].imm - pe.image_base
                current = tail_target
                continue
            direct_calls = [item for item in current_instructions if item.mnemonic == "call" and item.operands and item.operands[0].type == x86_const.X86_OP_IMM]
            if current_end - current_begin <= 220 and direct_calls:
                current = direct_calls[-1].operands[0].imm - pe.image_base
                continue
            core_begin, core_end, core_unwind = current_begin, current_end, current_unwind
            core_body, core_instructions = current_body, current_instructions
            core = {
                "beginRva": f"0x{core_begin:x}",
                "endRvaExclusive": f"0x{core_end:x}",
                "spanBytes": core_end - core_begin,
                "bodySha256": hashlib.sha256(core_body).hexdigest(),
                "unwindInfoRva": f"0x{core_unwind:x}",
                "firstInstructions": [
                    {"offset": f"0x{item.address - (pe.image_base + core_begin):x}", "mnemonic": item.mnemonic, "opStr": item.op_str}
                    for item in core_instructions[:16]
                ],
                "semantic": _core_semantic_fingerprint(core_instructions, core_begin, pe.image_base),
            }
            break
        if core is None:
            raise ContractError(f"Burst implementation chain for 0x{entry:x} did not reach a core")
        assignment_instruction = ins
        variant = "avx2" if any("ymm" in ins.op_str or ins.mnemonic.startswith("v") for ins in entry_instructions[:12]) else "x64_sse2"
        assignments.append({
            "initializerInstructionRva": f"0x{assignment_instruction.address - pe.image_base:x}",
            "implementationEntryRva": f"0x{begin:x}",
            "implementationEndRvaExclusive": f"0x{end:x}",
            "implementationSpanBytes": end - begin,
            "implementationBodySha256": hashlib.sha256(body).hexdigest(),
            "unwindInfoRva": f"0x{unwind:x}",
            "cpuVariant": variant,
            "tailJumpTargetRva": f"0x{tail_target:x}" if tail_target is not None else None,
            "callChain": chain,
            "core": core,
        })
    if len(assignments) != 2:
        raise ContractError(f"slot 0x{slot_rva:x} expected two CPU initializer assignments, found {len(assignments)}")
    assignments.sort(key=lambda row: row["cpuVariant"])
    if {row["cpuVariant"] for row in assignments} != {"avx2", "x64_sse2"}:
        raise ContractError(f"slot 0x{slot_rva:x} CPU variant set is not avx2/x64_sse2")
    return assignments


def _core_semantic_fingerprint(instructions: list[Any], core_begin: int, image_base: int) -> dict[str, Any]:
    """Extract bounded parameter/guard evidence from a generated core body."""
    if not instructions:
        raise ContractError(f"empty Burst core at 0x{core_begin:x}")
    # Recover stack-parameter offsets from the normal generated prologue.
    push_bytes = 0
    sub_bytes = None
    lea_add = None
    for ins in instructions[:32]:
        if ins.mnemonic == "push":
            push_bytes += 8
        elif ins.mnemonic == "sub" and len(ins.operands) == 2 and ins.reg_name(ins.operands[0].reg) == "rsp" and ins.operands[1].type == x86_const.X86_OP_IMM:
            sub_bytes = ins.operands[1].imm
        elif ins.mnemonic == "lea" and len(ins.operands) == 2 and ins.reg_name(ins.operands[0].reg) == "rbp" and ins.operands[1].type == x86_const.X86_OP_MEM and ins.reg_name(ins.operands[1].mem.base) == "rsp":
            lea_add = ins.operands[1].mem.disp
            break
    if sub_bytes is None or lea_add is None:
        raise ContractError(f"Burst core 0x{core_begin:x} has unsupported frame prologue")
    first_stack = push_bytes + sub_bytes - lea_add + 0x28
    registers: dict[str, str] = {"rcx": "param1", "rdx": "param2", "r8": "param3", "r9": "param4"}
    parameter_loads: list[dict[str, Any]] = []
    array_accesses: list[dict[str, Any]] = []
    index_param = None
    multiplier_evidence: list[dict[str, Any]] = []
    for ins in instructions:
        if ins.mnemonic in {"mov", "movsxd", "movsx", "movzx", "movss", "movsd", "vmovss", "vmovsd", "vmovups", "vmovdqu", "movups", "movdqu"} and len(ins.operands) >= 2:
            dst, src = ins.operands[0], ins.operands[1]
            if dst.type == x86_const.X86_OP_REG:
                mem = _memory_operand(ins, src, "rbp")
                if mem is not None:
                    param = _param_from_rbp_disp(mem.disp, first_stack_offset=first_stack)
                    if param is not None:
                        name = f"param{param}"
                        registers[ins.reg_name(dst.reg)] = name
                        parameter_loads.append({"instructionOffset": f"0x{ins.address - (image_base + core_begin):x}", "parameter": param, "register": ins.reg_name(dst.reg), "widthBytes": src.size})
            if src.type == x86_const.X86_OP_MEM:
                mem = src.mem
                base = ins.reg_name(mem.base)
                source = registers.get(base)
                if source is not None:
                    array_accesses.append({
                        "instructionOffset": f"0x{ins.address - (image_base + core_begin):x}",
                        "operation": ins.mnemonic,
                        "parameter": int(source.removeprefix("param")) if source.startswith("param") else source,
                        "base": base,
                        "scale": mem.scale,
                        "displacement": mem.disp,
                        "widthBytes": src.size,
                    })
        if ins.mnemonic == "imul" and len(ins.operands) >= 3 and ins.operands[2].type == x86_const.X86_OP_IMM:
            multiplier_evidence.append({
                "instructionOffset": f"0x{ins.address - (image_base + core_begin):x}",
                "register": ins.reg_name(ins.operands[0].reg),
                "immediate": ins.operands[2].imm,
            })
        if ins.mnemonic in {"mov", "movsxd", "movsx", "movzx"} and len(ins.operands) >= 2 and ins.operands[0].type == x86_const.X86_OP_REG and ins.operands[1].type == x86_const.X86_OP_REG:
            registers[ins.reg_name(ins.operands[0].reg)] = registers.get(ins.reg_name(ins.operands[1].reg), "unknown")
        if ins.mnemonic == "mov" and len(ins.operands) == 2 and ins.operands[0].type == x86_const.X86_OP_REG and ins.operands[1].type == x86_const.X86_OP_IMM:
            # Do not retain a stale parameter identity after a scalar constant.
            registers[ins.reg_name(ins.operands[0].reg)] = "constant"
        if ins.mnemonic in {"movsxd", "movzx", "movsx"} and len(ins.operands) >= 2 and ins.operands[1].type == x86_const.X86_OP_MEM:
            mem = ins.operands[1].mem
            base = ins.reg_name(mem.base)
            if base in registers and mem.index != 0 and ins.reg_name(mem.index) in registers:
                index_param = index_param or registers[ins.reg_name(mem.index)]
    parameter_names = {index: name for index, name in enumerate(CANONICAL_PARAMETERS, 1)}
    # The first guarded byte access is the most discriminating evidence: the
    # managed fallback tests flagArray (param 5), while unrelated generated
    # jobs often use another byte NativeArray in this position.
    byte_guards = [row for row in array_accesses if row["widthBytes"] == 1]
    first_byte_guard = byte_guards[0] if byte_guards else None
    word_accesses = [row for row in array_accesses if row["widthBytes"] == 2]
    return {
        "stackParameterOffsetFirst": f"0x{first_stack:x}",
        "parameterLoads": parameter_loads[:32],
        "arrayAccesses": array_accesses[:64],
        "firstByteGuard": first_byte_guard,
        "wordAccesses": word_accesses[:16],
        "indexParameterObserved": index_param,
        "strideMultipliers": multiplier_evidence[:32],
        "parameterNames": parameter_names,
    }


def _semantic_match(candidate: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    mapping = candidate["callMapping"]
    required = {
        "jobColliderIndexList": 1,
        "teamDataArray": 2,
        "teamIdArray": 4,
        "flagArray": 5,
        "framePositions": 7,
        "frameRotations": 8,
        "oldFramePositions": 10,
        "oldFrameRotations": 11,
        "nowPositions": 12,
        "nowRotations": 13,
        "oldPositions": 14,
        "oldRotations": 15,
        "workDataArray": 16,
        "lengthPtr": 17,
    }
    mapping_matches = {
        name: mapping["callArgumentSources"][param - 1] == f"param{param}"
        for name, param in required.items()
    }
    body_rows = {row["cpuVariant"]: row for row in candidate["initializerAssignments"]}
    core_fingerprints = {variant: body_rows[variant]["core"]["semantic"] for variant in ("avx2", "x64_sse2")}
    guard_matches: dict[str, Any] = {}
    for variant, fingerprint in core_fingerprints.items():
        guard = fingerprint.get("firstByteGuard")
        guard_matches[variant] = {
            "flagArrayParam5": bool(guard and guard.get("parameter") == 5 and guard.get("scale") == 1),
            "observed": guard,
            "indexParameter17": fingerprint.get("indexParameterObserved") in ("param17", 17),
            "teamIdWordParam4": any(row.get("parameter") == 4 and row.get("scale") == 2 for row in fingerprint.get("wordAccesses", [])),
            "teamDataStride464": any(row.get("immediate") == 0x1D0 for row in fingerprint.get("strideMultipliers", [])),
        }
    required_checks = {
        "canonicalParameterOrder": mapping["canonicalOrderExact"],
        "jobColliderIndexList": mapping_matches["jobColliderIndexList"],
        "teamDataArray": mapping_matches["teamDataArray"],
        "teamIdArray": mapping_matches["teamIdArray"],
        "flagArray": mapping_matches["flagArray"],
        "index": mapping_matches["lengthPtr"],
    }
    for variant, checks in guard_matches.items():
        required_checks[f"{variant}.flagArrayGuard"] = checks["flagArrayParam5"]
        required_checks[f"{variant}.index"] = checks["indexParameter17"]
        required_checks[f"{variant}.teamId"] = checks["teamIdWordParam4"]
        required_checks[f"{variant}.teamDataStride"] = checks["teamDataStride464"]
    return {
        "mappingMatches": mapping_matches,
        "guardMatches": guard_matches,
        "requiredChecks": required_checks,
        "allRequiredChecksPass": all(required_checks.values()),
        "comparisonBasis": {
            "managedFallbackMethodIndex": fallback["methodIndex"],
            "managedFallbackBodySha256": fallback["bodySha256"],
            "canonicalParameterNames": CANONICAL_PARAMETERS,
        },
    }


def _candidate_row(pe: PeImage, row: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    slot_rva, call, instructions, code = _find_call_slot(pe, row)
    body_bytes = instructions[-1].address + instructions[-1].size - instructions[0].address
    actual_body_sha = hashlib.sha256(code[:body_bytes]).hexdigest()
    if body_bytes != int(row["bodyBytes"]) or actual_body_sha != row["bodySha256"]:
        raise ContractError(
            f"candidate {row['hash']} body hash/boundary drift: "
            f"{body_bytes}/{actual_body_sha} != {row['bodyBytes']}/{row['bodySha256']}"
        )
    mapping = _candidate_call_mapping(instructions)
    assignments = _slot_assignments(pe, slot_rva)
    candidate = {
        "hash": row["hash"],
        "rva": row["rva"],
        "fileOffset": row["fileOffset"],
        "spanBytes": row["spanBytes"],
        "bodyBytes": row["bodyBytes"],
        "bodySha256": row["bodySha256"],
        "callSite": {
            "instructionOffset": f"0x{call.address - instructions[0].address:x}",
            "slotRva": f"0x{slot_rva:x}",
            "callEncoding": call.bytes.hex(),
        },
        "callMapping": mapping,
        "initializerAssignments": assignments,
    }
    candidate["semanticMatch"] = _semantic_match(candidate, fallback)
    return candidate


def _markdown(contract: dict[str, Any]) -> str:
    targets = contract["targets"]
    semantic = contract["semanticDecision"]
    lines = [
        "# Collider Start Burst semantic contract",
        "",
        f"Status: `{contract['status']}`.",
        "",
        "This report follows each opaque export's static function-pointer slot through the pinned CPU-variant initializers and compares the resulting implementation bodies with the canonical 17-parameter Collider Start signature and managed fallback. It does not assert that method 385416 selected any hash; runtime GetProcAddress telemetry remains the wrapper-to-hash gate.",
        "",
        "| Export candidate | Call order | AVX2 core | SSE2 core | Managed-fallback semantic match |",
        "|---|---|---|---|---|",
    ]
    for row in targets:
        cores = {item["cpuVariant"]: item["core"] for item in row["initializerAssignments"]}
        avx = cores["avx2"]["beginRva"] if cores.get("avx2") else "-"
        sse = cores["x64_sse2"]["beginRva"] if cores.get("x64_sse2") else "-"
        lines.append(f"| `{row['hash']}` | `{row['callMapping']['callArgumentSources']}` | `{avx}` | `{sse}` | `{row['semanticMatch']['allRequiredChecksPass']}` |")
    lines += [
        "",
        f"Semantic candidate: `{semantic['semanticCandidateHash']}`. Mapping status: `{semantic['wrapperToHashMappingStatus']}`.",
        "",
        "The semantic candidate is only a static export-body fingerprint. No Burst function pointer is loaded or called by this builder.",
        "",
    ]
    return "\n".join(lines)


def build_contract(*, game_assembly: Path | None = DEFAULT_GAME_ASSEMBLY,
                   metadata: Path | None = DEFAULT_METADATA) -> dict[str, Any]:
    gate = _native_gate(game_assembly, metadata)
    if Cs is None:
        raise ContractError(f"Capstone unavailable: {_CAPSTONE_IMPORT_ERROR}")
    ga = Path(gate["gameAssembly"]["path"])
    md_path = Path(gate["globalMetadata"]["path"])
    burst = Path(gate["libBurstGenerated"]["path"])
    fallback = _validate_solver_fallback()
    metadata_signature = _metadata_parameter_names(md_path)
    export = _load_burst_export_contract(ga, md_path)
    pe = PeImage(burst)
    targets = [_candidate_row(pe, export["rows"][hash_value], fallback) for hash_value in sorted(EXPECTED_CANDIDATE_HASHES)]
    matches = [row for row in targets if row["semanticMatch"]["allRequiredChecksPass"]]
    if len(matches) != 1:
        semantic_status = "bounded_semantic_candidate_set"
        semantic_hash = None
    else:
        semantic_status = "unique_static_semantic_candidate_wrapper_mapping_unresolved"
        semantic_hash = matches[0]["hash"]
    # This explicit negative assertion is part of the contract: the unique
    # semantic candidate must not be emitted as method-385416's runtime hash.
    decision = {
        "semanticCandidateHash": semantic_hash,
        "semanticCandidateCount": len(matches),
        "semanticCandidateReason": "only candidate whose canonical call order and both CPU-variant cores match managed fallback flagArray/teamIdArray/TeamData/index access evidence" if semantic_hash else "no unique candidate passed the canonical access checks",
        "wrapperToHashMappingStatus": "unresolved_runtime_GetProcAddress_required",
        "wrapperMethodIndex": 385416,
        "wrapperHashIdentityPublished": False,
    }
    return {
        "schema": "endfield.charinfo.secondary-dynamics-collider-start-semantics.v1",
        "status": semantic_status,
        "nativeGate": gate,
        "canonicalSignature": metadata_signature,
        "managedFallback": fallback,
        "candidateSource": {
            # The parent Burst-export builder is an implementation helper and
            # is edited independently.  Pin the consumed generated contract
            # below; do not make this report self-invalidating on unrelated
            # builder refactors.
            "builderPath": _path(BURST_EXPORT_BUILDER),
            "contract": _file(BURST_EXPORT_JSON),
            "candidateCount": len(targets),
            "candidateHashes": [row["hash"] for row in targets],
        },
        "targets": targets,
        "semanticDecision": decision,
        "boundary": [
            "The static export body can be semantically fingerprinted but cannot prove that BurstDirectCall method 385416 selected this export at runtime.",
            "No function pointer is loaded, called, or installed by this builder.",
            "A changed GameAssembly.dll, global-metadata.dat, or lib_burst_generated.dll fails the three-file gate and leaves the checked-in report untouched.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--check", action="store_true", help="verify checked-in JSON and Markdown without writing")
    args = parser.parse_args()
    try:
        contract = build_contract(game_assembly=args.game_assembly, metadata=args.metadata)
        serialized = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
        markdown = _markdown(contract)
        if args.check:
            json_matches = args.output.is_file() and args.output.read_text(encoding="utf-8") == serialized
            markdown_matches = args.markdown.is_file() and args.markdown.read_text(encoding="utf-8") == markdown
            print(json.dumps({"status": contract["status"], "jsonMatches": json_matches, "markdownMatches": markdown_matches, "output": str(args.output)}))
            return 0 if json_matches and markdown_matches else 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        args.markdown.write_text(markdown, encoding="utf-8")
        print(json.dumps({"status": contract["status"], "output": str(args.output), "markdown": str(args.markdown)}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, ContractError) as exc:
        print(json.dumps({"status": "unavailable", "validationFailures": [str(exc)]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
