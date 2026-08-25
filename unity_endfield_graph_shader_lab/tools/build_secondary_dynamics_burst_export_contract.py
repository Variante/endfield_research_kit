#!/usr/bin/env python3
"""Classify the pinned Burst hashed exports used by secondary dynamics.

The Burst DLL exports 628 opaque 32-hex names.  Those names are dispatch
wrappers: the executable does not contain their hash bytes, and there is no
static relocation from a managed BurstDirectCall to one of the names.  This
builder therefore records PE/function-boundary and x64 ABI evidence and
publishes *bounded candidates*, not a guessed hash-to-kernel mapping.

The native gate is deliberately the same two-input gate used by the other
secondary-dynamics contracts.  A Burst hash is accepted only for the exact
DLL SHA-256 pinned below, derived from the explicitly validated
GameAssembly.dll path.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
except ImportError as exc:  # pragma: no cover - environment gate
    Cs = None  # type: ignore[assignment]
    _CAPSTONE_IMPORT_ERROR = exc
else:
    _CAPSTONE_IMPORT_ERROR = None


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None
EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_LIB_BURST_SHA256 = "ee8702dd63dec2db7dc29d5bc23b8acd032f0e19a0daad5f69e6c45f9d3ceb99"
DEFAULT_OUTPUT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/secondary_dynamics_burst_export_contract.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    """Raised when a pinned native evidence gate does not close."""


def _validate_collider_wrapper_evidence(wrapper: dict[str, Any], expected_names: list[str]) -> None:
    """Fail closed on any thunk payload access, GPR clobber, or order drift."""
    if wrapper.get("incomingGprPreserved") != ["rcx", "rdx", "r8", "r9"]:
        raise ContractError("ColliderEnd thunk incoming GPR preservation drift")
    if wrapper.get("payloadDereferenceCount", 0) != 0 or wrapper.get("payloadWritebackCount", 0) != 0:
        raise ContractError("ColliderEnd thunk contains payload dereference/writeback")
    if wrapper.get("decodedForwardingParameterNames") != expected_names:
        raise ContractError("ColliderEnd thunk forwarding parameter order drift")


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
    result = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256, EXPECTED_METADATA_SHA256,
        gameassembly=game_assembly, metadata=metadata,
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
    burst_hash = _sha256(burst)
    if burst_hash != EXPECTED_LIB_BURST_SHA256:
        raise ContractError(f"lib_burst_generated.dll sha256 mismatch: {burst_hash}")
    return {
        "gameAssembly": _file(ga, result.gameassembly_sha256),
        "globalMetadata": _file(md, result.metadata_sha256),
        "libBurstGenerated": _file(burst, burst_hash),
    }


def _pe_exports(path: Path) -> dict[str, Any]:
    """Parse named exports and RVAs without pefile/capstone dependencies."""
    data = path.read_bytes()
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ContractError("pinned lib_burst_generated.dll is not a PE image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if pe + 24 > len(data) or data[pe:pe + 4] != b"PE\0\0":
        raise ContractError("pinned lib_burst_generated.dll has no PE signature")
    coff = pe + 4
    section_count = struct.unpack_from("<H", data, coff + 2)[0]
    optional_size = struct.unpack_from("<H", data, coff + 16)[0]
    optional = coff + 20
    if optional + optional_size > len(data) or struct.unpack_from("<H", data, optional)[0] != 0x20B:
        raise ContractError("pinned lib_burst_generated.dll is not PE32+")
    image_base = struct.unpack_from("<Q", data, optional + 24)[0]
    export_rva, export_size = struct.unpack_from("<II", data, optional + 112)
    if not export_rva or export_size < 40:
        raise ContractError("pinned lib_burst_generated.dll has no export directory")
    table = optional + optional_size
    sections: list[tuple[int, int, int]] = []
    section_records: list[dict[str, Any]] = []
    for index in range(section_count):
        row = table + index * 40
        if row + 40 > len(data):
            raise ContractError("truncated PE section table")
        raw_name = data[row:row + 8].rstrip(b"\0")
        try:
            section_name = raw_name.decode("ascii")
        except UnicodeDecodeError:
            section_name = raw_name.decode("ascii", errors="replace")
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
            "<IIII", data, row + 8
        )
        sections.append((virtual_address, max(virtual_size, raw_size), raw_pointer))
        section_records.append({
            "name": section_name,
            "virtualAddress": virtual_address,
            "virtualSize": virtual_size,
            "rawSize": raw_size,
            "rawPointer": raw_pointer,
        })

    def rva_offset(rva: int, size: int = 1) -> int:
        for virtual_address, section_size, raw_pointer in sections:
            if virtual_address <= rva and rva + size <= virtual_address + section_size:
                offset = raw_pointer + rva - virtual_address
                if 0 <= offset <= len(data) - size:
                    return offset
        raise ContractError(f"PE RVA 0x{rva:x} is outside sections")

    directory = rva_offset(export_rva, 40)
    (characteristics, timestamp, major, minor, name_rva, ordinal_base,
     function_count, name_count, functions_rva, names_rva,
     ordinals_rva) = struct.unpack_from("<IIHHIIIIIII", data, directory)
    del characteristics, timestamp, major, minor, name_rva
    if name_count > function_count or name_count > 1_000_000:
        raise ContractError("invalid PE export name/function counts")
    exports: list[dict[str, Any]] = []
    for index in range(name_count):
        name_pointer = struct.unpack_from("<I", data, rva_offset(names_rva + index * 4, 4))[0]
        name_offset = rva_offset(name_pointer)
        end = data.find(b"\0", name_offset)
        if end < 0:
            raise ContractError("unterminated PE export name")
        raw_name = data[name_offset:end]
        ordinal = struct.unpack_from("<H", data, rva_offset(ordinals_rva + index * 2, 2))[0]
        function_rva = struct.unpack_from(
            "<I", data, rva_offset(functions_rva + ordinal * 4, 4)
        )[0]
        try:
            name = raw_name.decode("ascii")
        except UnicodeDecodeError:
            name = raw_name.decode("ascii", errors="replace")
        exports.append({"name": name, "rva": function_rva, "ordinal": ordinal_base + ordinal})
    exports.sort(key=lambda row: (row["rva"], row["name"]))
    if not exports:
        raise ContractError("pinned lib_burst_generated.dll has no named exports")
    hashed = [row for row in exports if re.fullmatch(r"[0-9a-f]{32}", row["name"])]
    if len(hashed) != 628:
        raise ContractError(f"expected 628 hashed exports, found {len(hashed)}")
    return {
        "data": data,
        "sections": sections,
        "sectionRecords": section_records,
        "imageBase": image_base,
        "exportDirectoryRva": export_rva,
        "exportDirectorySize": export_size,
        "exports": exports,
        "hashed": hashed,
    }


def _stack_writes(body: bytes) -> list[dict[str, Any]]:
    raise AssertionError("_stack_writes requires decoded instructions")


def _decode_body(code: bytes, address: int) -> tuple[bytes, list[Any]]:
    if Cs is None:
        raise ContractError(f"Capstone unavailable: {_CAPSTONE_IMPORT_ERROR}")
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = True
    instructions = list(decoder.disasm(code, address))
    if not instructions:
        raise ContractError(f"no x64 instructions at 0x{address:x}")
    ret = next((ins for ins in instructions if ins.mnemonic == "ret"), None)
    if ret is None:
        raise ContractError(f"no real ret instruction at 0x{address:x}")
    end = ret.address - address + ret.size
    bounded = [ins for ins in instructions if ins.address < address + end]
    cursor = address
    for ins in bounded:
        if ins.address != cursor:
            raise ContractError(f"unsupported/undecoded x64 bytes at 0x{cursor:x}")
        cursor += ins.size
    if cursor != address + end:
        raise ContractError(f"incomplete x64 decode at 0x{cursor:x}")
    return code[:end], bounded


def _section_record(pe: dict[str, Any], rva: int, size: int = 1) -> dict[str, Any] | None:
    """Return the PE section containing an RVA, including zero-fill BSS."""
    for row in pe.get("sectionRecords", []):
        start = int(row["virtualAddress"])
        span = max(int(row["virtualSize"]), int(row["rawSize"]))
        if start <= rva and rva + size <= start + span:
            result = dict(row)
            result["rvaOffset"] = rva - start
            result["virtualEndExclusive"] = start + int(row["virtualSize"])
            result["rawEndExclusive"] = start + int(row["rawSize"])
            result["fileBacked"] = rva >= start and rva + size <= start + int(row["rawSize"])
            return result
    return None


def _rip_target(ins: Any, image_base: int) -> int | None:
    if not ins.operands:
        return None
    for operand in ins.operands:
        if operand.type == 3 and ins.reg_name(operand.mem.base) == "rip":
            return ins.address + ins.size + operand.mem.disp - image_base
    return None


def _direct_target(ins: Any, image_base: int) -> int | None:
    if ins.mnemonic not in {"call", "jmp"} or not ins.operands:
        return None
    operand = ins.operands[0]
    if operand.type != 2:
        return None
    return operand.imm - image_base


def _stack_move_fingerprint(instructions: list[Any], image_base: int,
                            function_address: int) -> dict[str, Any]:
    """Record ABI moves without inventing managed argument names."""
    loads: list[dict[str, Any]] = []
    stores: list[dict[str, Any]] = []
    for ins in instructions:
        if ins.mnemonic not in {"mov", "movss", "movsd"} or len(ins.operands) < 2:
            continue
        dst, src = ins.operands[0], ins.operands[1]
        if dst.type == 1 and src.type == 3 and ins.reg_name(src.mem.base) == "rbp":
            loads.append({
                "instructionOffset": f"0x{ins.address - function_address:x}",
                "sourceStackOffset": f"0x{src.mem.disp:x}",
                "destination": ins.reg_name(dst.reg),
                "widthBytes": 4 if ins.mnemonic == "movss" else 8,
                "kind": "xmm" if ins.mnemonic in {"movss", "movsd"} else "gpr",
            })
        if dst.type == 3 and ins.reg_name(dst.mem.base) == "rsp":
            source = ins.reg_name(src.reg) if src.type == 1 else None
            stores.append({
                "instructionOffset": f"0x{ins.address - function_address:x}",
                "destinationStackOffset": f"0x{dst.mem.disp:x}",
                "source": source,
                "widthBytes": 4 if ins.mnemonic == "movss" else 8,
                "kind": "xmm" if ins.mnemonic in {"movss", "movsd"} else "gpr",
            })
    calls: list[dict[str, Any]] = []
    direct_calls: list[dict[str, Any]] = []
    tail_transfers: list[dict[str, Any]] = []
    for ins in instructions:
        if ins.mnemonic == "call":
            rip = _rip_target(ins, image_base)
            direct = _direct_target(ins, image_base)
            if rip is not None:
                calls.append({
                    "instructionOffset": f"0x{ins.address - function_address:x}",
                    "kind": "indirect_rip_memory",
                    "targetRva": f"0x{rip:x}",
                })
            elif direct is not None:
                direct_calls.append({
                    "instructionOffset": f"0x{ins.address - function_address:x}",
                    "kind": "direct_relative",
                    "targetRva": f"0x{direct:x}",
                })
            else:
                calls.append({
                    "instructionOffset": f"0x{ins.address - function_address:x}",
                    "kind": "indirect_register_or_memory",
                })
        elif ins.mnemonic == "jmp":
            rip = _rip_target(ins, image_base)
            direct = _direct_target(ins, image_base)
            row: dict[str, Any] = {"instructionOffset": f"0x{ins.address - function_address:x}"}
            if rip is not None:
                row.update(kind="indirect_rip_memory", targetRva=f"0x{rip:x}")
            elif direct is not None:
                row.update(kind="direct_relative", targetRva=f"0x{direct:x}")
            else:
                row["kind"] = "indirect_register_or_memory"
            tail_transfers.append(row)
    return {
        "stackLoads": loads,
        "stackStores": stores,
        "calls": calls,
        "directCalls": direct_calls,
        "tailTransfers": tail_transfers,
    }


def _memory_operand(ins: Any, operand: Any, base: str) -> dict[str, Any] | None:
    if operand.type != 3 or ins.reg_name(operand.mem.base) != base:
        return None
    return {"offset": operand.mem.disp, "widthBytes": operand.size}


def _stack_writes_from_instructions(instructions: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ins in instructions:
        if ins.mnemonic not in {"mov", "movss", "movsd"} or not ins.operands:
            continue
        memory = _memory_operand(ins, ins.operands[0], "rsp")
        if memory is not None:
            if ins.mnemonic == "movss":
                memory["widthBytes"] = 4
                memory["kind"] = "xmm"
            elif ins.mnemonic == "movsd":
                memory["widthBytes"] = 8
                memory["kind"] = "xmm"
            rows.append(memory)
    return sorted(rows, key=lambda row: (row["offset"], row["widthBytes"], row.get("kind", "gpr")))


def _stack_load_registers(body: bytes) -> list[str]:
    raise AssertionError("_stack_load_registers requires decoded instructions")


def _stack_load_registers_from_instructions(instructions: list[Any]) -> list[str]:
    result: list[str] = []
    for ins in instructions:
        if ins.mnemonic != "mov" or len(ins.operands) < 2 or ins.operands[0].type != 1:
            continue
        memory = _memory_operand(ins, ins.operands[1], "rbp")
        if memory is None:
            continue
        result.append(ins.reg_name(ins.operands[0].reg))
    return result


def _xmm_stack_load_count(body: bytes) -> int:
    raise AssertionError("_xmm_stack_load_count requires decoded instructions")


def _xmm_stack_load_count_from_instructions(instructions: list[Any]) -> int:
    return sum(
        ins.mnemonic in {"movss", "movsd"}
        and len(ins.operands) >= 2
        and _memory_operand(ins, ins.operands[1], "rbp") is not None
        for ins in instructions
    )


def _body_rows(pe: dict[str, Any]) -> list[dict[str, Any]]:
    data = pe["data"]
    hashed = pe["hashed"]
    rows: list[dict[str, Any]] = []
    for index, export in enumerate(hashed):
        next_rva = hashed[index + 1]["rva"] if index + 1 < len(hashed) else None
        span = (next_rva - export["rva"]) if next_rva is not None else None
        if span is None or span <= 0:
            # The final hash is followed by padding and non-hash exports.  Use
            # the containing section end as the outer bound; its first ret is
            # still the valid generated-wrapper boundary.
            section_end = next((va + size for va, size, _ in pe["sections"]
                                if va <= export["rva"] < va + size), None)
            if section_end is None:
                raise ContractError(f"final hashed export 0x{export['rva']:x} is outside PE sections")
            span = section_end - export["rva"]
        file_offset = None
        for virtual_address, section_size, raw_pointer in pe["sections"]:
            if virtual_address <= export["rva"] < virtual_address + section_size:
                file_offset = raw_pointer + export["rva"] - virtual_address
                break
        if file_offset is None or file_offset >= len(data):
            raise ContractError(f"hashed export 0x{export['rva']:x} is outside PE sections")
        span = min(span, len(data) - file_offset)
        code = data[file_offset:file_offset + span]
        body, instructions = _decode_body(code, pe["imageBase"] + export["rva"])
        stores = _stack_writes_from_instructions(instructions)
        loads = _stack_load_registers_from_instructions(instructions)
        rows.append({
            "hash": export["name"],
            "ordinal": export["ordinal"],
            "rva": f"0x{export['rva']:x}",
            "fileOffset": f"0x{file_offset:x}",
            "spanBytes": span,
            "bodyBytes": len(body),
            "bodySha256": hashlib.sha256(body).hexdigest(),
            "retBoundary": "decoded_ret",
            "stackWrites": stores,
            "stackWriteOffsets": [f"0x{row['offset']:x}" for row in stores],
            "stackWriteWidths": [row["widthBytes"] for row in stores],
            "stackLoadRegisterDestinations": loads,
            "incomingGprClobbers": sorted(set(loads) & {"rcx", "rdx", "r8", "r9"}),
            "xmmStackLoadCount": _xmm_stack_load_count_from_instructions(instructions),
            "indirectRipCallCount": body.count(b"\xff\x15"),
        })
    return rows


def _rva_file_offset(pe: dict[str, Any], rva: int, size: int = 1) -> int:
    """Return the raw-file offset for one RVA in the pinned PE image."""

    if size < 0:
        raise ContractError("negative PE read size")
    row = _section_record(pe, rva, size)
    if row is not None and row["fileBacked"]:
        offset = int(row["rawPointer"]) + int(row["rvaOffset"])
        if 0 <= offset <= len(pe["data"] ) - size:
            return offset
    if row is not None and not row["fileBacked"]:
        raise ContractError(f"PE RVA 0x{rva:x} is zero-fill and has no raw-file offset")
    raise ContractError(f"PE RVA 0x{rva:x} is outside sections")


def _exact_rva_span(
    pe: dict[str, Any],
    rva: int,
    size: int,
    expected_sha256: str,
) -> tuple[bytes, list[Any]]:
    """Read and continuously disassemble one hash-pinned PE code span."""
    if Cs is None:
        raise ContractError(f"Capstone unavailable: {_CAPSTONE_IMPORT_ERROR}")
    offset = _rva_file_offset(pe, rva, size)
    body = pe["data"][offset:offset + size]
    actual_sha256 = hashlib.sha256(body).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ContractError(
            f"exact Burst span 0x{rva:x} hash drift: {actual_sha256}"
        )
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = True
    instructions = list(decoder.disasm(body, pe["imageBase"] + rva))
    if not instructions:
        raise ContractError(f"exact Burst span 0x{rva:x} did not disassemble")
    cursor = pe["imageBase"] + rva
    for ins in instructions:
        if ins.address != cursor:
            raise ContractError(f"exact Burst span decode gap at 0x{cursor:x}")
        cursor += ins.size
    if cursor != pe["imageBase"] + rva + size:
        raise ContractError(f"exact Burst span 0x{rva:x} decode ended early")
    return body, instructions


def _named_export_body(pe: dict[str, Any], export: dict[str, Any]) -> tuple[bytes, list[Any]]:
    """Decode one named initializer through its first real ret.

    The IMAGE_EXPORT_DIRECTORY has no size for a function body.  The next
    named export is used only as an outer bound; Capstone's first real ret is
    the published body boundary.  This is deliberately the same bounded
    approach used for hashed exports above.
    """

    exports = pe["exports"]
    index = next((i for i, row in enumerate(exports) if row is export), None)
    if index is None:
        index = next((i for i, row in enumerate(exports) if row["name"] == export["name"] and row["rva"] == export["rva"]), None)
    if index is None:
        raise ContractError(f"named export row is not present: {export}")
    next_rva = exports[index + 1]["rva"] if index + 1 < len(exports) else None
    if next_rva is None or next_rva <= export["rva"]:
        section_end = next((va + size for va, size, _ in pe["sections"]
                            if va <= export["rva"] < va + size), None)
        if section_end is None:
            raise ContractError(f"named export 0x{export['rva']:x} has no section bound")
        next_rva = section_end
    file_offset = _rva_file_offset(pe, export["rva"])
    span = min(next_rva - export["rva"], len(pe["data"]) - file_offset)
    return _decode_body(
        pe["data"][file_offset:file_offset + span],
        pe["imageBase"] + export["rva"],
    )


def _rip_memory_target(pe: dict[str, Any], ins: Any) -> int | None:
    """Resolve an instruction's RIP-relative memory operand, if present."""

    for operand in ins.operands:
        if operand.type == 3 and ins.reg_name(operand.mem.base) == "rip":
            return ins.address + ins.size + operand.mem.disp
    return None


def _rip_store_rows(pe: dict[str, Any], body_start: int, instructions: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ins in instructions:
        if ins.mnemonic != "mov" or len(ins.operands) < 2:
            continue
        target = _rip_memory_target(pe, ins)
        if target is None or ins.operands[1].type != 1:
            continue
        rows.append({
            "instructionOffset": f"0x{ins.address - body_start:x}",
            "targetVa": f"0x{target:x}",
            "targetRva": f"0x{target - pe['imageBase']:x}",
            "sourceRegister": ins.reg_name(ins.operands[1].reg),
            "widthBytes": ins.operands[0].size,
        })
    return rows


def _rip_call_rows(pe: dict[str, Any], body_start: int, instructions: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ins in instructions:
        if ins.mnemonic != "call" or not ins.operands:
            continue
        target = _rip_memory_target(pe, ins)
        if target is not None:
            rows.append({
                "instructionOffset": f"0x{ins.address - body_start:x}",
                "targetVa": f"0x{target:x}",
                "targetRva": f"0x{target - pe['imageBase']:x}",
                "kind": "indirect_rip_call",
            })
            continue
        operand = ins.operands[0]
        if operand.type == 1:
            rows.append({
                "instructionOffset": f"0x{ins.address - body_start:x}",
                "register": ins.reg_name(operand.reg),
                "kind": "indirect_register_call",
            })
    return rows


def _read_cstring(pe: dict[str, Any], va: int) -> str:
    """Read one bounded initializer string from a PE data section."""

    rva = va - pe["imageBase"]
    offset = _rva_file_offset(pe, rva)
    section_end = next((int(row["rawPointer"]) + int(row["rawSize"])
                        for row in pe.get("sectionRecords", [])
                        if int(row["virtualAddress"]) <= rva < int(row["virtualAddress"]) + max(int(row["virtualSize"]), int(row["rawSize"]))), len(pe["data"]))
    end = pe["data"].find(b"\0", offset, min(len(pe["data"]), section_end))
    if end < 0:
        raise ContractError(f"unterminated Burst initializer string at 0x{va:x}")
    try:
        value = pe["data"][offset:end].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ContractError(f"non-ASCII Burst initializer string at 0x{va:x}") from exc
    if not value or len(value) > 256:
        raise ContractError(f"invalid Burst initializer string length at 0x{va:x}")
    return value


def _initializer_row(pe: dict[str, Any], exports_by_name: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
    export = exports_by_name.get(name)
    if export is None:
        raise ContractError(f"missing pinned Burst initializer export: {name}")
    body, instructions = _named_export_body(pe, export)
    body_start = pe["imageBase"] + export["rva"]
    return {
        "name": name,
        "rva": f"0x{export['rva']:x}",
        "bodyBytes": len(body),
        "bodySha256": hashlib.sha256(body).hexdigest(),
        "branchCount": sum(ins.mnemonic.startswith(("j", "loop")) for ins in instructions),
        "instructions": instructions,
        "bodyStart": body_start,
        "body": body,
        "ripStores": _rip_store_rows(pe, body_start, instructions),
        "ripCalls": _rip_call_rows(pe, body_start, instructions),
    }


def _candidate_initializer_evidence(
    pe: dict[str, Any],
    candidate_hash: str,
    slot_va: int,
) -> dict[str, Any]:
    """Pin resolver/static initializer edges for one hash slot.

    These are initialization edges only.  The returned function pointer is
    intentionally not called or promoted to a Burst-kernel identity.
    """

    exports_by_name = {row["name"]: row for row in pe["exports"]}
    variants: dict[str, Any] = {}
    for family in ("externals", "statics"):
        family_rows: list[dict[str, Any]] = []
        for variant in ("avx2", "x64_sse2"):
            name = f"burst.initialize.{family}.{candidate_hash}_{variant}"
            row = _initializer_row(pe, exports_by_name, name)
            evidence: dict[str, Any] = {
                "name": row["name"],
                "rva": row["rva"],
                "bodyBytes": row["bodyBytes"],
                "bodySha256": row["bodySha256"],
                "branchCount": row["branchCount"],
                "storesRaxCount": sum(store["sourceRegister"] == "rax" for store in row["ripStores"]),
                "storesRaxTargets": row["ripStores"],
            }
            if family == "externals":
                callback_moves = [ins for ins in row["instructions"]
                                  if ins.mnemonic == "mov" and len(ins.operands) >= 2
                                  and ins.operands[0].type == 1 and ins.operands[1].type == 1
                                  and ins.reg_name(ins.operands[0].reg) == "rsi"
                                  and ins.reg_name(ins.operands[1].reg) == "rcx"]
                resolver_calls = [call for call in row["ripCalls"]
                                  if call.get("kind") == "indirect_register_call"
                                  and call.get("register") == "rsi"]
                resolver_strings: list[str] = []
                for ins in row["instructions"]:
                    if ins.mnemonic != "lea" or len(ins.operands) < 2:
                        continue
                    if ins.operands[0].type != 1 or ins.reg_name(ins.operands[0].reg) != "rcx":
                        continue
                    target = _rip_memory_target(pe, ins)
                    if target is not None:
                        resolver_strings.append(_read_cstring(pe, target))
                if len(callback_moves) != 1 or not resolver_calls or len(resolver_calls) != len(resolver_strings):
                    raise ContractError(f"{name} resolver callback CFG drift")
                evidence.update({
                    "callbackArgumentRegister": "rcx",
                    "callbackWorkingRegister": "rsi",
                    "resolverCallCount": len(resolver_calls),
                    "resolverStrings": resolver_strings,
                    "candidateWrapperSlotStoreMatches": [store for store in row["ripStores"]
                                                         if int(store["targetVa"], 16) == slot_va],
                })
            else:
                selector_constants = [int(ins.operands[1].imm) for ins in row["instructions"]
                                      if ins.mnemonic == "movabs" and len(ins.operands) >= 2
                                      and ins.operands[0].type == 1 and ins.reg_name(ins.operands[0].reg) == "rax"
                                      and ins.operands[1].type == 2]
                evidence.update({
                    "staticSelectorConstants": [f"0x{value & ((1 << 64) - 1):x}" for value in selector_constants],
                    "staticIndirectCallCount": len(row["ripCalls"]),
                    "candidateWrapperSlotStoreMatches": [store for store in row["ripStores"]
                                                         if int(store["targetVa"], 16) == slot_va],
                })
            family_rows.append(evidence)
        variants[family] = family_rows
    return variants


def _collider_end_exact_export_identity(
    pe: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Close the hash/slot/core graph for Collider End on the pinned DLL."""
    candidate_hash = "b44b8d6a5416f62541c69d9812961578"
    export_row = next((row for row in rows if row["hash"] == candidate_hash), None)
    if export_row is None:
        raise ContractError(f"missing exact Collider End export {candidate_hash}")
    expected_export = {
        "rva": "0x358a20",
        "bodyBytes": 30,
        "bodySha256": "73942dc01488235175d3a865b0fcf1224444f595672b1d9bd569cd488c1b7998",
    }
    if any(export_row.get(key) != value for key, value in expected_export.items()):
        raise ContractError("exact Collider End export row drift")
    export = next(
        (row for row in pe["hashed"] if row["name"] == candidate_hash), None
    )
    if export is None:
        raise ContractError("exact Collider End named export is absent")
    export_body, export_instructions = _named_export_body(pe, export)
    if hashlib.sha256(export_body).hexdigest() != expected_export["bodySha256"]:
        raise ContractError("exact Collider End export body drift")
    export_calls = [
        _rip_memory_target(pe, ins)
        for ins in export_instructions
        if ins.mnemonic == "call"
    ]
    slot_va = pe["imageBase"] + 0x3C6060
    if export_calls != [slot_va]:
        raise ContractError(f"exact Collider End export slot drift: {export_calls}")

    variants = []
    specifications = (
        {
            "cpuVariant": "x64_sse2",
            "initializerRva": 0x35FD5A,
            "initializerSha256": "167ef99ed3801301d660b9b0043e5ee94494cd4aa257d4d109f7a09bc0c3d462",
            "entryRva": 0xAE190,
            "entryBytes": 29,
            "entrySha256": "9296e922d0ad7deda2a97fcd64f672ee6c9a1d012ddf882fc63b226c436eb7d7",
            "coreRva": 0xAE300,
            "coreBytes": 113,
            "coreSha256": "dc805b6764831250c6ea08d93c17f002c826abd8c8bd23b8a3362f150175a100",
        },
        {
            "cpuVariant": "avx2",
            "initializerRva": 0x35BB23,
            "initializerSha256": "a63c0d4c8d859c1a4ea8aab1b71900e9236944239086cb17784ea9ea6aee8fa7",
            "entryRva": 0x24A030,
            "entryBytes": 29,
            "entrySha256": "9296e922d0ad7deda2a97fcd64f672ee6c9a1d012ddf882fc63b226c436eb7d7",
            "coreRva": 0x24A1A0,
            "coreBytes": 117,
            "coreSha256": "fe354aabb5d9e1763b597a9f72608fe0a9ee62ab962ef451ea6515cf6137d97c",
        },
    )
    for spec in specifications:
        init_body, init_instructions = _exact_rva_span(
            pe, spec["initializerRva"], 14, spec["initializerSha256"]
        )
        if [ins.mnemonic for ins in init_instructions] != ["lea", "mov"]:
            raise ContractError("Collider End burst.initialize assignment shape drift")
        init_targets = [
            _rip_memory_target(pe, ins) for ins in init_instructions
        ]
        expected_targets = [
            pe["imageBase"] + spec["entryRva"], slot_va
        ]
        if init_targets != expected_targets:
            raise ContractError(
                f"Collider End {spec['cpuVariant']} initializer target drift: "
                f"{init_targets}"
            )

        _entry_body, entry_instructions = _exact_rva_span(
            pe, spec["entryRva"], spec["entryBytes"], spec["entrySha256"]
        )
        direct_calls = [
            _direct_target(ins, pe["imageBase"])
            for ins in entry_instructions
            if ins.mnemonic == "call"
        ]
        if direct_calls != [spec["coreRva"]]:
            raise ContractError(
                f"Collider End {spec['cpuVariant']} entry-to-core edge drift"
            )

        _core_body, core_instructions = _exact_rva_span(
            pe, spec["coreRva"], spec["coreBytes"], spec["coreSha256"]
        )
        core_by_offset = {
            ins.address - pe["imageBase"] - spec["coreRva"]: ins
            for ins in core_instructions
        }
        expected_sites = {
            0x05: ("mov", "rax, qword ptr [rcx + 0x50]"),
            0x0F: ("mov", "rdx, qword ptr [rcx]"),
            0x12: ("mov", "r8, qword ptr [rcx + 0x10]"),
            0x16: ("mov", "r9, qword ptr [rcx + 0x30]"),
            0x1A: ("mov", "r10, qword ptr [rcx + 0x20]"),
            0x1E: ("mov", "rcx, qword ptr [rcx + 0x40]"),
        }
        for offset, expected in expected_sites.items():
            ins = core_by_offset.get(offset)
            if ins is None or (ins.mnemonic, ins.op_str) != expected:
                raise ContractError(
                    f"Collider End {spec['cpuVariant']} payload site 0x{offset:x} drift"
                )
        # The SSE2 and AVX2 encodings differ only by VEX prefixes here. Pin
        # the index arithmetic and the source/destination operands by suffix.
        text = [f"{ins.mnemonic} {ins.op_str}" for ins in core_instructions]
        required_suffixes = (
            "rsi, [rsi + rsi*2]",
            "xmmword ptr [r8 + rsi]",
            "qword ptr [r8 + rsi + 0x10]",
            "qword ptr [r9 + rsi + 0x10], xmm1",
            "xmmword ptr [r9 + rsi], xmm0",
            "r11, 4",
            "xmmword ptr [r10 + r11]",
            "xmmword ptr [rcx + r11], xmm0",
        )
        for suffix in required_suffixes:
            if not any(row.endswith(suffix) for row in text):
                raise ContractError(
                    f"Collider End {spec['cpuVariant']} semantic site missing: {suffix}"
                )
        variants.append({
            "cpuVariant": spec["cpuVariant"],
            "burstInitializeAssignment": {
                "rva": f"0x{spec['initializerRva']:x}",
                "bytes": len(init_body),
                "sha256": spec["initializerSha256"],
                "entryRva": f"0x{spec['entryRva']:x}",
                "functionPointerSlotRva": "0x3c6060",
            },
            "entry": {
                "rva": f"0x{spec['entryRva']:x}",
                "bytes": spec["entryBytes"],
                "sha256": spec["entrySha256"],
            },
            "core": {
                "rva": f"0x{spec['coreRva']:x}",
                "bytes": spec["coreBytes"],
                "sha256": spec["coreSha256"],
            },
        })
    return {
        "status": "static_export_slot_and_dual_cpu_core_identity_closed",
        "hash": candidate_hash,
        "ordinal": export_row["ordinal"],
        "export": {
            "rva": export_row["rva"],
            "bodyBytes": export_row["bodyBytes"],
            "bodySha256": export_row["bodySha256"],
            "functionPointerSlotRva": "0x3c6060",
        },
        "variants": variants,
        "payload": {
            "jobColliderIndexListOffset": "0x0",
            "nowPositionsOffset": "0x10",
            "nowRotationsOffset": "0x20",
            "oldPositionsOffset": "0x30",
            "oldRotationsOffset": "0x40",
            "indexCountOffset": "0x50",
            "positionStrideBytes": 24,
            "rotationStrideBytes": 16,
            "operation": [
                "oldPositions[index] = nowPositions[index]",
                "oldRotations[index] = nowRotations[index]",
            ],
        },
        "managedWrapperMapping": "semantic_identity_closed_runtime_GetProcAddress_route_unobserved",
    }


def _collider_end_candidate_audit(pe: dict[str, Any], rows: list[dict[str, Any]], gate: dict[str, Any]) -> dict[str, Any]:
    """Compare both end-range candidates against the known managed fallback.

    The result is intentionally an exclusion audit: neither candidate is
    promoted.  The Burst body is only a two-stack-argument forwarding thunk;
    the six managed parameter names and the now/old array offsets come from
    the exact GameAssembly/metadata-derived contracts already checked by this
    builder's sibling contracts.
    """

    candidate_hashes = ("5d15fdfe5676d33316f2415a1f41d523", "e6aec003f0525fe127cd9c0ccb59b1e2")
    exact_identity = _collider_end_exact_export_identity(pe, rows)
    solver_path = DEFAULT_OUTPUT.parent / "secondary_dynamics_solver_static_contract.json"
    job_path = DEFAULT_OUTPUT.parent / "secondary_dynamics_job_layout_contract.json"
    solver_provenance = _rebuild_sibling_contract(
        solver_path.name, gate, "endfield.charinfo.secondary-dynamics-solver-static.v1", "native_spans_hash_pinned"
    )
    job_provenance = _rebuild_sibling_contract(
        job_path.name, gate, "endfield.charinfo.secondary-dynamics-job-layout.v1", "outer_job_layout_closed"
    )
    solver_payload = json.loads(solver_path.read_text(encoding="utf-8"))
    job_payload = json.loads(job_path.read_text(encoding="utf-8"))
    fallback_rows = [row for row in solver_payload.get("targets", [])
                     if row.get("methodIndex") == 385455]
    if (len(fallback_rows) != 1 or
            fallback_rows[0].get("solverStatus") !=
            "managed_fallback_state_carry_forward_closed"):
        raise ContractError("managed ColliderManager End Execute(int) fallback identity drift")
    fallback = fallback_rows[0]
    expected_transitions = [
        ("nowPositions", "oldPositions", "Unity.Mathematics.double3", 24),
        ("nowRotations", "oldRotations", "Unity.Mathematics.quaternion", 16),
    ]
    actual_transitions = [
        (
            row.get("sourceField"),
            row.get("destinationField"),
            row.get("elementType"),
            row.get("widthBytes"),
        )
        for row in fallback.get("stateTransitions", [])
        if row.get("operation") == "copy"
    ]
    if actual_transitions != expected_transitions:
        raise ContractError(
            "managed ColliderManager End state carry-forward semantics drift"
        )
    expected_accesses = {
        "nowPositions": ("0x10", 24, [0, 16]),
        "nowRotations": ("0x20", 16, [0]),
        "oldPositions": ("0x30", 24, [0, 16]),
        "oldRotations": ("0x40", 16, [0]),
    }
    actual_accesses = {row.get("jobField"): row for row in fallback.get("bufferAccesses", [])}
    if not set(expected_accesses) <= set(actual_accesses):
        raise ContractError(f"managed ColliderManager End fallback field set drift: {sorted(actual_accesses)}")
    managed_fields: list[dict[str, Any]] = []
    for name, (offset, stride, displacements) in expected_accesses.items():
        row = actual_accesses[name]
        if (row.get("jobOffset"), row.get("strideBytes"), row.get("elementFieldDisplacements")) != (offset, stride, displacements):
            raise ContractError(f"managed ColliderManager End fallback access drift for {name}")
        managed_fields.append({
            "name": name,
            "jobOffset": offset,
            "strideBytes": stride,
            "elementFieldDisplacements": displacements,
            "instructionOffsets": row.get("instructionOffsets"),
        })
    jobs = [row for row in job_payload.get("jobs", [])
            if row.get("type") == "BeyondDynamicBone.ColliderManager+EndSimulationStepJob"]
    if len(jobs) != 1:
        raise ContractError("canonical ColliderManager End job layout identity drift")
    job_fields = jobs[0].get("fields", [])
    expected_job_names = ["jobColliderIndexList", "nowPositions", "nowRotations", "oldPositions", "oldRotations", "_indexCount"]
    if [row.get("name") for row in job_fields] != expected_job_names:
        raise ContractError("canonical ColliderManager End job field order drift")
    expected_job_schema = [
        ("jobColliderIndexList", "NativeArray", "System.Int32", 4),
        ("nowPositions", "NativeArray", "Unity.Mathematics.double3", 24),
        ("nowRotations", "NativeArray", "Unity.Mathematics.quaternion", 16),
        ("oldPositions", "NativeArray", "Unity.Mathematics.double3", 24),
        ("oldRotations", "NativeArray", "Unity.Mathematics.quaternion", 16),
        ("_indexCount", "NativeReference", "System.Int32", 4),
    ]
    actual_job_schema = [(row.get("name"), row.get("kind"), row.get("elementType", {}).get("name"), row.get("elementType", {}).get("nativeSizeBytes")) for row in job_fields]
    if actual_job_schema != expected_job_schema:
        raise ContractError(f"canonical ColliderManager End job schema drift: {actual_job_schema}")
    by_hash = {row["hash"]: row for row in rows}
    semantic_cores = {
        "5d15fdfe5676d33316f2415a1f41d523": {
            "status": "incompatible_with_canonical_job_element_strides",
            "reason": "The core indexes position rows at 12 bytes and copies float3 plus quaternion; canonical now/old positions are double3 at 24 bytes.",
            "variants": (("AVX2", 0x24D8D0, 0x61, "2c13d41676b518db37f84558a675726189ca29ffc4fadb757af6f8ef921bc0e1"),
                         ("SSE2", 0xB2E80, 0x5F, "fa0774f9c385ab162d8e03093ee29d2bbd3af70ab544b99fd943f447bd8c25e6")),
        },
        "e6aec003f0525fe127cd9c0ccb59b1e2": {
            "status": "incompatible_with_direct_invoke_container_abi",
            "reason": "The core treats the first incoming lane as a scalar count and operates on 184-byte records, rather than consuming six container pointers.",
            "variants": (("AVX2", 0x2A0670, 0x23D, "ed1dfada261fad7c4a7a63f9987d11e4edf34f99a99290e278d6c457a5eff9c9"),
                         ("SSE2", 0x117860, 0x2CE, "166dda52f397ef0c4d56d544bf30a1f3d0345153a9494d30447b4c63e3177a86")),
        },
    }
    candidates: list[dict[str, Any]] = []
    for candidate_hash in candidate_hashes:
        row = by_hash[candidate_hash]
        export_rva = int(row["rva"], 16)
        file_offset = int(row["fileOffset"], 16)
        body, instructions = _decode_body(
            pe["data"][file_offset:file_offset + row["spanBytes"]],
            pe["imageBase"] + export_rva,
        )
        if any(ins.mnemonic.startswith(("j", "loop")) for ins in instructions):
            raise ContractError(f"candidate {candidate_hash} gained a branch")
        indirect_calls = _rip_call_rows(pe, pe["imageBase"] + export_rva, instructions)
        if len(indirect_calls) != 1 or indirect_calls[0].get("kind") != "indirect_rip_call":
            raise ContractError(f"candidate {candidate_hash} does not have one RIP-indirect thunk call")
        slot_va = int(indirect_calls[0]["targetVa"], 16)
        call_index = next(i for i, ins in enumerate(instructions) if ins.mnemonic == "call")
        written_before_call = {ins.reg_name(ins.operands[0].reg) for ins in instructions[:call_index]
                               if ins.operands and ins.operands[0].type == 1}
        incoming_preserved = [reg for reg in ("rcx", "rdx", "r8", "r9") if reg not in written_before_call]
        payload_accesses = [
            {"instructionOffset": f"0x{ins.address - (pe['imageBase'] + export_rva):x}",
             "operand": ins.op_str, "access": "write" if index == 0 else "read"}
            for ins in instructions for index, operand in enumerate(ins.operands)
            if operand.type == 3 and ins.reg_name(operand.mem.base) not in {"rbp", "rsp", "rip"}
        ]
        payload_dereference_count = len(payload_accesses)
        payload_writeback_count = sum(row["access"] == "write" for row in payload_accesses)
        stack_loads = []
        stack_forwards = []
        for ins in instructions:
            if ins.mnemonic != "mov" or len(ins.operands) < 2:
                continue
            if ins.operands[0].type == 1 and ins.operands[1].type == 3:
                source = ins.operands[1]
                if ins.reg_name(source.mem.base) == "rbp":
                    stack_loads.append({
                        "instructionOffset": f"0x{ins.address - (pe['imageBase'] + export_rva):x}",
                        "source": f"[rbp+0x{source.mem.disp:x}]",
                        "destinationRegister": ins.reg_name(ins.operands[0].reg),
                        "widthBytes": ins.operands[0].size,
                        "parameter": job_fields[4 + len(stack_loads)].get("name"),
                    })
            if ins.operands[0].type == 3 and ins.operands[1].type == 1:
                dest = ins.operands[0]
                if ins.reg_name(dest.mem.base) == "rsp":
                    stack_forwards.append({
                        "instructionOffset": f"0x{ins.address - (pe['imageBase'] + export_rva):x}",
                        "destination": f"[rsp+0x{dest.mem.disp:x}]",
                        "sourceRegister": ins.reg_name(ins.operands[1].reg),
                        "widthBytes": dest.size,
                        "parameter": job_fields[4 if dest.mem.disp == 0x20 else 5].get("name"),
                    })
        if stack_loads != [
            {"instructionOffset": "0xa", "source": "[rbp+0x30]", "destinationRegister": "rax", "widthBytes": 8, "parameter": "oldRotations"},
            {"instructionOffset": "0xe", "source": "[rbp+0x38]", "destinationRegister": "r10", "widthBytes": 8, "parameter": "_indexCount"},
        ]:
            raise ContractError(f"candidate {candidate_hash} stack parameter forwarding drift")
        if stack_forwards != [
            {"instructionOffset": "0x12", "destination": "[rsp+0x28]", "sourceRegister": "r10", "widthBytes": 8, "parameter": "_indexCount"},
            {"instructionOffset": "0x17", "destination": "[rsp+0x20]", "sourceRegister": "rax", "widthBytes": 8, "parameter": "oldRotations"},
        ]:
            raise ContractError(f"candidate {candidate_hash} outgoing stack forwarding drift")
        candidate_wrapper = {
                "rva": row["rva"],
                "bodyBytes": row["bodyBytes"],
                "bodySha256": row["bodySha256"],
                "branchCount": sum(ins.mnemonic.startswith(("j", "loop")) for ins in instructions),
                "incomingGprPreserved": incoming_preserved,
                "decodedForwardingParameterNames": [job_fields[index].get("name") for index in range(4)] + [entry["parameter"] for entry in stack_loads],
                "payloadAccesses": payload_accesses,
                "payloadDereferenceCount": payload_dereference_count,
                "payloadWritebackCount": payload_writeback_count,
                "indirectCall": indirect_calls[0],
                "incomingGprForwarding": [
                    {"ordinal": index + 1, "parameter": job_fields[index].get("name"), "register": register}
                    for index, register in enumerate(("rcx", "rdx", "r8", "r9"))
                ],
                "stackParameterForwarding": stack_loads,
                "outgoingStackForwarding": stack_forwards,
            }
        _validate_collider_wrapper_evidence(candidate_wrapper, [field.get("name") for field in job_fields])
        semantic = semantic_cores[candidate_hash]
        variants = []
        for architecture, core_rva, core_size, expected_hash in semantic["variants"]:
            offset = _rva_file_offset(pe, core_rva, core_size)
            actual_hash = hashlib.sha256(pe["data"][offset:offset + core_size]).hexdigest()
            if actual_hash != expected_hash:
                raise ContractError(f"candidate {candidate_hash} {architecture} core hash drift")
            variants.append({"architecture": architecture, "rva": f"0x{core_rva:x}",
                             "spanBytes": core_size, "bodySha256": actual_hash})
        candidates.append({
            "hash": candidate_hash,
            "wrapper": candidate_wrapper,
            "semanticCompatibility": {"status": semantic["status"], "reason": semantic["reason"],
                                      "coreVariants": variants},
            "runtimeFunctionPointerSlot": {
                "targetVa": f"0x{slot_va:x}",
                "targetRva": f"0x{slot_va - pe['imageBase']:x}",
                "initializers": _candidate_initializer_evidence(pe, candidate_hash, slot_va),
            },
        })

    parameter_rows = []
    for ordinal, field in enumerate(job_fields, 1):
        kind = field.get("kind")
        element = field.get("elementType", {}).get("name")
        parameter_rows.append({"ordinal": ordinal, "name": field.get("name"),
                               "kind": f"{kind}<{element}>" if element else kind})
    wrapper_forwarding_equal = all(c["wrapper"]["incomingGprForwarding"] == candidates[0]["wrapper"]["incomingGprForwarding"] for c in candidates)
    stack_forwarding_equal = all(c["wrapper"]["stackParameterForwarding"] == candidates[0]["wrapper"]["stackParameterForwarding"] and c["wrapper"]["outgoingStackForwarding"] == candidates[0]["wrapper"]["outgoingStackForwarding"] for c in candidates)
    slot_rvas = [c["runtimeFunctionPointerSlot"]["targetRva"] for c in candidates]
    return {
        "status": "static_semantic_export_identity_closed_managed_wrapper_route_unobserved",
        "parameterContract": {
            "methodIndex": 385317,
            "method": "Invoke",
            "parameterCount": 6,
            "parameters": parameter_rows,
            "source": "canonical EndSimulationStepJob field metadata",
        },
        "managedFallbackComparison": {
            "methodIndex": 385455,
            "method": "BeyondDynamicBone.ColliderManager+EndSimulationStepJob.Execute(int)",
            "source": _path(solver_path),
            "sourceSha256": _sha256(solver_path),
            "bodySha256": fallback.get("bodySha256"),
            "fields": managed_fields,
            "stateCarryForward": [
                {
                    "sourceField": source,
                    "destinationField": destination,
                    "elementType": element_type,
                    "widthBytes": width,
                }
                for source, destination, element_type, width
                in actual_transitions
            ],
            "boundary": "managed fallback accesses are evidence of the six-container job layout, not evidence that either hashed export is the fallback or Burst kernel",
        },
        "canonicalJobLayout": {
            "source": _path(job_path),
            "sourceSha256": _sha256(job_path),
            "type": jobs[0].get("type"),
            "nativeSizeBytes": jobs[0].get("nativeSizeBytes"),
            "fields": [
                {
                    "name": row.get("name"),
                    "boxedFieldOffset": row.get("boxedFieldOffset"),
                    "nativePayloadOffset": row.get("nativePayloadOffset"),
                    "kind": row.get("kind"),
                    "elementType": row.get("elementType", {}).get("name"),
                    "elementNativeSizeBytes": row.get("elementType", {}).get("nativeSizeBytes"),
                }
                for row in job_fields
            ],
        },
        "provenance": {"solver": solver_provenance, "jobLayout": job_provenance},
        "exactSemanticExport": exact_identity,
        "comparison": {
            "candidateCount": len(candidates),
            "semanticCompatibleCandidateCount": 1,
            "sameWrapperCfg": all(c["wrapper"]["branchCount"] == candidates[0]["wrapper"]["branchCount"] and c["wrapper"]["indirectCall"]["kind"] == candidates[0]["wrapper"]["indirectCall"]["kind"] for c in candidates),
            "sameParameterForwarding": wrapper_forwarding_equal and stack_forwarding_equal,
            "sameNativeArrayParameterOrder": all(c["wrapper"]["decodedForwardingParameterNames"] == [field.get("name") for field in job_fields] for c in candidates),
            "fieldOffsetsPresentInCandidateThunk": any(c["wrapper"]["payloadDereferenceCount"] for c in candidates),
            "nowOldWritebackDiscriminates": len({c["wrapper"]["payloadWritebackCount"] for c in candidates}) > 1,
            "staticInitializerSlotIdentityDiscriminates": True,
            "wrapperSlotsDistinct": len(set(slot_rvas)) > 1,
            "runtimeSelectedPointerObserved": False,
            "externalInitializerRequiresRuntimeCallback": any(bool(c["runtimeFunctionPointerSlot"]["initializers"].get("externals")) for c in candidates),
            "requiredNextEvidence": "runtime GetProcAddress/resolver callback trace only to close managed BurstDirectCall wrapper-to-hash selection; export b44b8d6a5416f62541c69d9812961578 and both CPU cores are already statically closed",
        },
        "candidates": candidates,
        "nonClaims": [
            "Neither retained ABI-shape candidate is compatible with EndSimulationStepRangeKernel semantics; the static filter is incomplete.",
            "The monolithic burst.initialize assignment closes the exact hashed export slot and dual-CPU cores, but does not prove that managed BurstDirectCall selected the hash at runtime.",
            "Managed now/old position and rotation writebacks do not distinguish a wrapper that contains no job-field accesses.",
        ],
    }


def _target_candidates(pe: dict[str, Any], rows: list[dict[str, Any]], gate: dict[str, Any]) -> dict[str, Any]:
    by_hash = {row["hash"]: row for row in rows}
    stores = lambda row: [(int(offset, 16), width) for offset, width in zip(row["stackWriteOffsets"], row["stackWriteWidths"])]
    simulation_shape = lambda row: stores(row) == [(0x20, 4)] + [(offset, 8) for offset in range(0x28, 0xE1, 8)] and row["xmmStackLoadCount"] == 1
    sim_all = [row for row in rows if simulation_shape(row)]
    sim_qword = [row for row in sim_all if stores(row)[-1][1] == 8]
    collider_shape = lambda row: stores(row) == [(offset, 8) for offset in range(0x20, 0x80, 8)] + [(0x80, 4)]
    collider_all = [row for row in rows if collider_shape(row)]
    collider_dword = [row for row in collider_all if stores(row)[-1][1] == 4]
    end_shape = lambda row: stores(row) == [(0x20, 8), (0x28, 8)] and not row["incomingGprClobbers"]
    end_all = [row for row in rows if len(stores(row)) == 2 and stores(row)[0][0] == 0x20 and stores(row)[1][0] == 0x28 and stores(row)[0][1] == 8 and stores(row)[1][1] == 8]
    end_preserved = [row for row in end_all if not row["incomingGprClobbers"]]
    def brief(row: dict[str, Any]) -> dict[str, Any]:
        return {key: row[key] for key in ("hash", "rva", "spanBytes", "bodyBytes", "bodySha256", "stackWriteOffsets", "stackWriteWidths", "incomingGprClobbers")}
    end_audit = _collider_end_candidate_audit(pe, rows, gate)
    return {
        "simulationStartRange": {
            "managedMethodIndex": 385542,
            "directInvokeMethodIndex": 385570,
            "directInvokeVa": "0x1867775fc",
            "parameterContract": {
                "parameterCount": 29, "leadingSingleCount": 5,
                "directInvokeNativeArrayParameterCount": 24,
                "sourceJobNativeArrayFieldCount": 23,
                "sourceJobNativeReferenceFieldCount": 1,
                "lastParameter": "lengthPtr NativeArray<int> (direct ABI) / _indexCount NativeReference<int> (source job)",
            },
            "status": "unique_abi_candidate_identity_unresolved" if len(sim_qword) == 1 else "bounded_candidate_set",
            "candidates": [brief(row) for row in sim_qword],
            "nearCandidatesExcluded": [brief(row) for row in sim_all if row not in sim_qword],
            "exclusionReason": "08401c... has the same 24 stack slots but writes the final slot at width 4; metadata identifies lengthPtr as NativeArray<int>, so only the qword form is ABI-compatible.",
        },
        "colliderStartRange": {
            "managedMethodIndex": 385394,
            "directInvokeMethodIndex": 385416,
            "directInvokeVa": "0x186762cc0",
            "parameterContract": {"parameterCount": 17, "nativeArrayCount": 16, "lastParameter": "index System.Int32"},
            "status": "bounded_candidate_set" if len(collider_dword) > 1 else "unique_abi_candidate_identity_unresolved",
            "candidates": [brief(row) for row in collider_dword],
            "nearCandidatesExcluded": [brief(row) for row in collider_all if row not in collider_dword],
            "exclusionReason": "The six-slot-shape lookalikes either marshal 13 qword slots (NativeArray-like final value) or 16/17 stack slots; the target's final index is a dword and the direct invoke writes 13 slots.",
        },
        "colliderEndRange": {
            "managedMethodIndex": 385295,
            "directInvokeMethodIndex": 385317,
            "directInvokeVa": "0x18675b0cc",
            "parameterContract": {
                "parameterCount": 6,
                "directInvokeNativeArrayParameterCount": 6,
                "sourceJobNativeArrayFieldCount": 5,
                "sourceJobNativeReferenceFieldCount": 1,
                "stackDirectInvokeNativeArrayParameterCount": 2,
                "lastParameter": "lengthPtr NativeArray<int> (direct ABI) / _indexCount NativeReference<int> (source job)",
            },
            "status": "static_semantic_export_identity_closed_managed_wrapper_route_unobserved",
            "candidates": [brief(by_hash["b44b8d6a5416f62541c69d9812961578"])],
            "abiShapeFalseCandidates": [brief(row) for row in end_preserved],
            "nearCandidatesExcluded": [brief(row) for row in end_all if row not in end_preserved],
            "exclusionReason": "The old six-parameter thunk filter omitted the real struct-payload export b44b8d6a... and retained two false candidates whose cores violate the canonical job layout. Whole-DLL semantic scanning plus burst.initialize slot assignment closes b44b8d6a... instead.",
            "candidateAudit": end_audit,
        },
    }


def _managed_layout_cross_check() -> dict[str, Any]:
    """Cross-check Start/End job containers without conflating NativeReference with ABI slots."""
    path = DEFAULT_OUTPUT.parent / "secondary_dynamics_job_layout_contract.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ContractError(f"cannot read managed job layout for Burst fingerprint: {exc}") from exc
    jobs = {row.get("type"): row for row in payload.get("jobs", [])
            if row.get("type") in {
                "BeyondDynamicBone.SimulationManager+StartSimulationStepJob",
                "BeyondDynamicBone.SimulationManager+EndSimulationStepJob",
            }}
    expected_types = {
        "BeyondDynamicBone.SimulationManager+StartSimulationStepJob",
        "BeyondDynamicBone.SimulationManager+EndSimulationStepJob",
    }
    missing = sorted(expected_types - jobs.keys())
    if missing:
        raise ContractError(f"missing managed SimulationManager job layouts: {missing}")
    job = jobs["BeyondDynamicBone.SimulationManager+StartSimulationStepJob"]
    fields = job.get("fields", [])
    native_arrays = [row for row in fields if row.get("kind") == "NativeArray"]
    native_references = [row for row in fields if row.get("kind") == "NativeReference"]
    scalar_fields = [row for row in fields if row.get("kind") not in {"NativeArray", "NativeReference"}]
    # The managed job has 23 NativeArray fields plus a trailing
    # NativeReference<int> (_indexCount).  The Burst range ABI still exposes
    # that length pointer as the trailing (24th) container for the focused
    # kernel, but it must not be misreported as a NativeArray in the outer job
    # layout.
    if len(fields) != 26 or len(native_arrays) != 23:
        raise ContractError(
            f"managed SimulationManager Start job field drift: fields={len(fields)} nativeArrays={len(native_arrays)}"
        )
    if [row.get("name") for row in scalar_fields] != ["simulationPower", "simulationDeltaTime"]:
        raise ContractError("managed scalar prefix drift in SimulationManager Start job")
    if len(native_references) != 1 or native_references[0].get("name") != "_indexCount":
        raise ContractError("managed SimulationManager Start job _indexCount kind drift")
    if native_references[0].get("kind") != "NativeReference":
        raise ContractError("managed SimulationManager Start job _indexCount declaration drift")

    def describe_end_job(end_job: dict[str, Any]) -> dict[str, Any]:
        end_fields = end_job.get("fields", [])
        end_arrays = [row for row in end_fields if row.get("kind") == "NativeArray"]
        end_refs = [row for row in end_fields if row.get("kind") == "NativeReference"]
        end_scalars = [row for row in end_fields
                       if row.get("kind") not in {"NativeArray", "NativeReference"}]
        if (len(end_fields), len(end_scalars), len(end_arrays), len(end_refs)) != (17, 1, 15, 1):
            raise ContractError(
                "managed SimulationManager End job field drift: "
                f"fields={len(end_fields)} scalars={len(end_scalars)} "
                f"nativeArrays={len(end_arrays)} nativeReferences={len(end_refs)}"
            )
        if end_scalars[0].get("name") != "simulationDeltaTime" or end_refs[0].get("name") != "_indexCount":
            raise ContractError("managed SimulationManager End job scalar/reference drift")
        return {
            "source": _path(path),
            "schema": payload.get("schema"),
            "status": payload.get("status"),
            "jobType": end_job.get("type"),
            "nativeSizeBytes": end_job.get("nativeSizeBytes"),
            "fieldCount": len(end_fields),
            "scalarPrefix": [{"name": end_scalars[0].get("name"), "argumentIndexes": [0]}],
            "nativeArrayCount": len(end_arrays),
            "nativeReferenceCount": len(end_refs),
            "managedNativeContainerCount": len(end_arrays) + len(end_refs),
            "nativeArrayArgumentIndexes": list(range(1, 1 + len(end_arrays))),
            "nativeReferenceFields": [{
                "argumentIndex": 1 + len(end_arrays),
                "name": end_refs[0].get("name"),
                "nativePayloadOffset": end_refs[0].get("nativePayloadOffset"),
                "slotWidthBytes": end_refs[0].get("slotWidthBytes"),
                "elementType": end_refs[0].get("elementType", {}).get("name"),
            }],
            "nativeArrayFields": [
                {
                    "argumentIndex": 1 + index,
                    "name": row.get("name"),
                    "nativePayloadOffset": row.get("nativePayloadOffset"),
                    "slotWidthBytes": row.get("slotWidthBytes"),
                    "elementType": row.get("elementType", {}).get("name"),
                }
                for index, row in enumerate(end_arrays)
            ],
            "boundary": "managed metadata only; no EndSimulation Burst target identity inferred",
        }

    start_container_count = len(native_arrays) + len(native_references)
    if start_container_count != 24:
        raise ContractError(f"managed SimulationManager Start job container count drift: {start_container_count}")
    start_length_argument_index = 5 + len(native_arrays)
    return {
        "source": _path(path),
        "schema": payload.get("schema"),
        "status": payload.get("status"),
        "jobType": job.get("type"),
        "nativeSizeBytes": job.get("nativeSizeBytes"),
        "fieldCount": len(fields),
        "nativeReferenceCount": len(native_references),
        "managedNativeContainerCount": start_container_count,
        "scalarPrefix": [
            {"name": "simulationPower", "componentCount": 4, "argumentIndexes": [0, 1, 2, 3]},
            {"name": "simulationDeltaTime", "componentCount": 1, "argumentIndexes": [4]},
        ],
        "nativeArrayCount": len(native_arrays),
        "nativeArrayArgumentIndexes": list(range(5, 5 + len(native_arrays))),
        "nativeReferenceArgumentIndexes": [start_length_argument_index],
        "nativeReferenceFields": [
            {
                "argumentIndex": start_length_argument_index,
                "name": native_references[0].get("name"),
                "nativePayloadOffset": native_references[0].get("nativePayloadOffset"),
                "slotWidthBytes": native_references[0].get("slotWidthBytes"),
                "elementType": native_references[0].get("elementType", {}).get("name"),
            }
        ],
        "nativeArrayFields": [
            {
                "argumentIndex": 5 + index,
                "name": row.get("name"),
                "nativePayloadOffset": row.get("nativePayloadOffset"),
                "slotWidthBytes": row.get("slotWidthBytes"),
                "elementType": row.get("elementType", {}).get("name"),
            }
            for index, row in enumerate(native_arrays)
        ],
        "managedDirectInvokeContract": {
            "parameterCount": 29,
            "leadingScalarCount": 5,
            "containerArgumentCount": 24,
            "directInvokeNativeArrayParameterCount": 24,
            "sourceJobNativeArrayFieldCount": 23,
            "sourceJobNativeReferenceFieldCount": 1,
            "lengthPointerArgumentIndex": start_length_argument_index,
            "lengthPointerType": "NativeArray<int>",
            "boundary": "Burst direct-invoke ABI spelling; the corresponding managed job field is NativeReference<int>",
        },
        "endSimulation": describe_end_job(jobs["BeyondDynamicBone.SimulationManager+EndSimulationStepJob"]),
        "boundary": "managed metadata names and slot widths only; no Burst target identity inferred",
    }


def _simulation_semantic_fingerprint(pe: dict[str, Any], rows: list[dict[str, Any]],
                                     gate: dict[str, Any]) -> dict[str, Any]:
    candidate_hash = "c7e2be088565d3ff7a6e7ba86d23fd51"
    export = next((row for row in pe["hashed"] if row["name"] == candidate_hash), None)
    if export is None:
        raise ContractError(f"missing pinned Simulation ABI candidate export {candidate_hash}")
    row = next((row for row in rows if row["hash"] == candidate_hash), None)
    if row is None:
        raise ContractError(f"missing decoded row for Simulation ABI candidate {candidate_hash}")
    body_bytes, instructions = _named_export_body(pe, export)
    body_sha256 = hashlib.sha256(body_bytes).hexdigest()
    if body_sha256 != row["bodySha256"]:
        raise ContractError(
            f"Simulation candidate body hash drift: decoded={body_sha256} row={row['bodySha256']}"
        )
    fingerprint = _stack_move_fingerprint(
        instructions, pe["imageBase"], pe["imageBase"] + export["rva"]
    )
    indirect = [call for call in fingerprint["calls"] if call["kind"] == "indirect_rip_memory"]
    if len(indirect) != 1:
        raise ContractError(f"Simulation candidate expected one RIP-indirect call, found {len(indirect)}")
    target_rva = int(indirect[0]["targetRva"], 16)
    target_section = _section_record(pe, target_rva, 8)
    if target_section is None:
        raise ContractError(f"Simulation candidate indirect target leaves image: 0x{target_rva:x}")
    # The wrapper's function-pointer cell is in the virtual .data tail.  It is
    # not a file-backed pointer and must not be decoded as a static code RVA.
    if target_section["name"] != ".data" or target_section["fileBacked"]:
        raise ContractError(
            "Simulation candidate target slot changed from the pinned zero-fill .data boundary: "
            f"{target_section['name']} fileBacked={target_section['fileBacked']}"
        )
    expected_static = [
        f"burst.initialize.statics.{candidate_hash}_x64_sse2",
        f"burst.initialize.statics.{candidate_hash}_avx2",
    ]
    expected_external = [
        f"burst.initialize.externals.{candidate_hash}_x64_sse2",
        f"burst.initialize.externals.{candidate_hash}_avx2",
    ]
    by_name = {item["name"]: item for item in pe["exports"]}
    initializer_exports: list[dict[str, Any]] = []
    for name in expected_external + expected_static:
        item = by_name.get(name)
        if item is None:
            raise ContractError(f"missing candidate initializer export {name}")
        init_body, init_instructions = _named_export_body(pe, item)
        init_fingerprint = _stack_move_fingerprint(
            init_instructions, pe["imageBase"], pe["imageBase"] + item["rva"]
        )
        decoded = {
            "name": item["name"],
            "rva": f"0x{item['rva']:x}",
            "bodyBytes": len(init_body),
            "bodySha256": hashlib.sha256(init_body).hexdigest(),
            "retBoundary": "decoded_ret",
            "fingerprint": init_fingerprint,
        }
        calls = init_fingerprint["calls"]
        decoded["initializerRole"] = "externals" if ".externals." in name else "statics"
        decoded["runtimeBoundary"] = (
            "host callback GetProcAddress names; no kernel identity"
            if ".externals." in name else
            "BurstCompilerService shared-memory registration; no kernel identity"
        )
        if ".statics." in name:
            key_values = [int(ins.operands[1].imm) & ((1 << 64) - 1) for ins in init_instructions if ins.mnemonic == "movabs" and len(ins.operands) >= 2 and ins.reg_name(ins.operands[0].reg) == "rax"]
            size_values = [int(ins.operands[1].imm) for ins in init_instructions if ins.mnemonic == "mov" and len(ins.operands) >= 2 and ins.reg_name(ins.operands[0].reg) == "edx" and ins.operands[1].type == 2]
            alignment_values = [int(ins.operands[1].imm) for ins in init_instructions if ins.mnemonic == "mov" and len(ins.operands) >= 2 and ins.reg_name(ins.operands[0].reg) == "r8d" and ins.operands[1].type == 2]
            if key_values != [0xedfccb8b263b8f83] or size_values != [0x80000] or alignment_values != [0x10]:
                raise ContractError(f"{name} shared-memory argument decode drift")
            decoded["sharedMemoryKey"] = f"0x{key_values[0]:x}"
            decoded["sharedMemorySizeBytes"] = f"0x{size_values[0]:x}"
            decoded["sharedMemoryAlignmentBytes"] = alignment_values[0]
            decoded["sharedMemoryCallTargetRvas"] = sorted({
                f"0x{int(call['targetRva'], 16):x}"
                for call in calls if call.get("kind") == "indirect_rip_memory"
            })
        else:
            decoded["externalCallbackCount"] = len(calls)
        initializer_exports.append(decoded)
    if fingerprint["directCalls"] or fingerprint["tailTransfers"]:
        raise ContractError("Simulation candidate unexpectedly gained direct calls or tail transfers")
    if len(fingerprint["stackLoads"]) != 25 or len(fingerprint["stackStores"]) != 25:
        raise ContractError(
            "Simulation candidate ABI move drift: "
            f"loads={len(fingerprint['stackLoads'])} stores={len(fingerprint['stackStores'])}"
        )
    expected_loads = [("0xd0", "xmm4", 4)] + [
        (f"0x{offset:x}", register, 8)
        for offset, register in zip(
            list(range(0x128, 0x198, 8)) + list(range(0x120, 0xd0, -8)),
            ["r14", "r15", "r12", "r13", "rbx", "rdi", "rsi", "r11", "r10", "r9", "r8", "rdx", "rcx", "rax"] + ["rax"] * 10,
        )
    ]
    actual_loads = [(row["sourceStackOffset"], row["destination"], row["widthBytes"]) for row in fingerprint["stackLoads"]]
    expected_stores = [(f"0x{offset:x}", source, width) for offset, source, width in [
        (0xe0, "rax", 8), (0xd8, "rcx", 8), (0xd0, "rdx", 8), (0xc8, "r8", 8), (0xc0, "r9", 8),
        (0xb8, "r10", 8), (0xb0, "r11", 8), (0xa8, "rsi", 8), (0xa0, "rdi", 8), (0x98, "rbx", 8),
        (0x90, "r13", 8), (0x88, "r12", 8), (0x80, "r15", 8), (0x78, "r14", 8),
        (0x70, "rax", 8), (0x68, "rax", 8), (0x60, "rax", 8), (0x58, "rax", 8), (0x50, "rax", 8),
        (0x48, "rax", 8), (0x40, "rax", 8), (0x38, "rax", 8), (0x30, "rax", 8), (0x28, "rax", 8), (0x20, "xmm4", 4),
    ]]
    actual_stores = [(row["destinationStackOffset"], row["source"], row["widthBytes"]) for row in fingerprint["stackStores"]]
    if actual_loads != expected_loads or actual_stores != expected_stores:
        raise ContractError("Simulation candidate exact ABI load/store mapping drift")
    return {
        "status": "export_thunk_fingerprint_closed_internal_target_unobserved",
        "candidateHash": candidate_hash,
        "export": {
            "rva": row["rva"],
            "fileOffset": row["fileOffset"],
            "spanBytes": row["spanBytes"],
            "bodyBytes": row["bodyBytes"],
            "bodySha256": row["bodySha256"],
            "retBoundary": row["retBoundary"],
        },
        "abi": {
            "leadingScalarCount": 5,
            "leadingScalarRegisters": ["xmm0", "xmm1", "xmm2", "xmm3", "xmm4"],
            "directInvokeNativeArrayParameterCount": 24,
            "sourceJobNativeArrayFieldCount": 23,
            "sourceJobNativeReferenceFieldCount": 1,
            "stackInputLoads": fingerprint["stackLoads"],
            "stackOutputStores": fingerprint["stackStores"],
            "directCalls": fingerprint["directCalls"],
            "tailTransfers": fingerprint["tailTransfers"],
        },
        "indirectTarget": {
            "instructionOffset": indirect[0]["instructionOffset"],
            "kind": indirect[0]["kind"],
            "targetRva": indirect[0]["targetRva"],
            "targetVa": f"0x{pe['imageBase'] + target_rva:x}",
            "section": target_section["name"],
            "sectionVirtualRange": {
                "start": f"0x{target_section['virtualAddress']:x}",
                "endExclusive": f"0x{target_section['virtualEndExclusive']:x}",
            },
            "sectionRawRange": {
                "start": f"0x{target_section['virtualAddress']:x}",
                "endExclusive": f"0x{target_section['rawEndExclusive']:x}",
            },
            "fileBacked": False,
            "diskState": "zero_fill_bss_no_on_disk_pointer",
            "runtimeValue": "unobserved",
            "runtimeGate": "GetProcAddress returned function pointer trace required",
        },
        "initializerExports": initializer_exports,
        "managedCrossCheck": _managed_layout_cross_check(),
        "internalCfg": {
            "status": "unavailable_target_pointer_unobserved",
            "maxDepth": 0,
            "recursionBound": {"maxDepth": 4, "maxNodes": 128, "maxEdges": 256},
            "seedTargetRva": f"0x{target_rva:x}",
            "nodes": [],
            "edges": [],
            "reason": "The only call target is a zero-fill .data function-pointer cell. No static code RVA exists to recurse into.",
        },
        "jobPayload": {
            "status": "unavailable_target_pointer_unobserved",
            "nativeArrayFieldAccesses": [],
            "strideBytes": [],
            "constants": [],
            "writebacks": [],
            "reason": "Payload/stride/constant/writeback claims require the runtime-resolved kernel body; the export thunk alone only proves ABI moves.",
        },
        "sourcePins": {
            "gameAssemblySha256": gate["gameAssembly"]["sha256"],
            "globalMetadataSha256": gate["globalMetadata"]["sha256"],
            "libBurstGeneratedSha256": gate["libBurstGenerated"]["sha256"],
        },
        "identityBoundary": "unique_abi_candidate_identity_unresolved",
    }


def _contract_snapshot(name: str) -> dict[str, Any]:
    path = DEFAULT_OUTPUT.parent / name
    if not path.is_file():
        return {"path": _path(path), "status": "missing"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"path": _path(path), "status": "unreadable", "detail": str(exc)}
    return {"path": _path(path), "schema": payload.get("schema"), "status": payload.get("status")}


def _sibling_provenance(name: str, gate: dict[str, Any], expected_schema: str,
                        expected_status: str, require_burst: bool = False) -> dict[str, Any]:
    """Load a sibling contract only when its identity and source file are pinned."""
    path = DEFAULT_OUTPUT.parent / name
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ContractError(f"cannot read sibling contract {name}: {exc}") from exc
    if payload.get("schema") != expected_schema or payload.get("status") != expected_status:
        raise ContractError(f"sibling contract {name} schema/status drift")
    native = payload.get("nativeGate", payload.get("native_gate", {}))
    for key in ("gameAssembly", "globalMetadata"):
        if native.get(key, {}).get("sha256") != gate[key]["sha256"]:
            raise ContractError(f"sibling contract {name} native gate drift: {key}")
    if require_burst and native.get("libBurstGenerated", {}).get("sha256") != gate["libBurstGenerated"]["sha256"]:
        raise ContractError(f"sibling contract {name} Burst gate drift")
    # Validate every embedded sourceSha256 whose source exists locally.
    def verify_sources(value: Any) -> None:
        if isinstance(value, dict):
            source, digest = value.get("source"), value.get("sourceSha256")
            if source and digest:
                source_path = Path(source)
                if not source_path.is_absolute():
                    source_path = REPO_ROOT / source_path
                if source_path.is_file() and _sha256(source_path) != digest:
                    raise ContractError(f"sibling contract {name} source hash drift: {source}")
            for child in value.values():
                verify_sources(child)
        elif isinstance(value, list):
            for child in value:
                verify_sources(child)
    verify_sources(payload)
    return {"path": _path(path), "fileSha256": _sha256(path), "schema": payload["schema"],
            "status": payload["status"], "nativeGate": native}


def _rebuild_sibling_contract(name: str, gate: dict[str, Any], expected_schema: str,
                              expected_status: str, require_burst: bool = False) -> dict[str, Any]:
    """Rebuild a sibling contract in-process and require canonical byte identity."""
    path = DEFAULT_OUTPUT.parent / name
    module_path = LAB_ROOT / "tools" / ("build_" + name.replace(".json", ".py"))
    spec = importlib.util.spec_from_file_location(f"endfield_provenance_{path.stem}", module_path)
    if spec is None or spec.loader is None:
        raise ContractError(f"cannot import sibling builder {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    kwargs = {"gameassembly": Path(gate["gameAssembly"]["path"]),
              "metadata": Path(gate["globalMetadata"]["path"])}
    if name == "secondary_dynamics_job_layout_contract.json":
        kwargs = {"game_assembly": kwargs["gameassembly"], "metadata": kwargs["metadata"]}
    elif name == "secondary_dynamics_solver_static_contract.json":
        kwargs = {"gameassembly": kwargs["gameassembly"], "metadata": kwargs["metadata"]}
    rebuilt = module.build_contract(**kwargs)
    if rebuilt.get("schema") != expected_schema or rebuilt.get("status") != expected_status:
        raise ContractError(f"rebuilt sibling contract {name} schema/status drift")
    if require_burst:
        native = rebuilt.get("nativeGate", rebuilt.get("native_gate", {}))
        if native.get("libBurstGenerated", {}).get("sha256") != gate["libBurstGenerated"]["sha256"]:
            raise ContractError(f"rebuilt sibling contract {name} Burst gate drift")
    canonical = json.dumps(rebuilt, indent=2, ensure_ascii=False) + "\n"
    actual = path.read_text(encoding="utf-8")
    if canonical != actual:
        raise ContractError(f"sibling contract {name} is not canonical rebuild output")
    return {"path": _path(path), "fileSha256": _sha256(path), "rebuiltCanonicalSha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "schema": rebuilt["schema"], "status": rebuilt["status"]}


def _validate_solver_identity_contract(gate: dict[str, Any]) -> dict[str, Any]:
    path = DEFAULT_OUTPUT.parent / "secondary_dynamics_solver_static_contract.json"
    if not path.is_file():
        raise ContractError(f"missing solver static contract: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        method_ids = {row["methodIndex"] for row in payload.get("targets", [])}
        for row in payload.get("targets", []):
            method_ids.update(call.get("methodIndex") for call in row.get("nextCalls", []) if call.get("methodIndex") is not None)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ContractError(f"invalid solver static contract: {exc}") from exc
    required = {385542, 385570, 385394, 385295}
    missing = sorted(required - method_ids)
    if missing:
        raise ContractError(f"solver static contract missing target method identities: {missing}")
    wrapper_path = DEFAULT_OUTPUT.parent / "secondary_dynamics_burst_wrapper_contract.json"
    if not wrapper_path.is_file():
        raise ContractError(f"missing Burst wrapper contract: {wrapper_path}")
    try:
        wrapper = json.loads(wrapper_path.read_text(encoding="utf-8"))
        rows = {row["methodIndex"]: row for row in wrapper.get("targets", [])}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ContractError(f"invalid Burst wrapper contract: {exc}") from exc
    wrapper_provenance = _rebuild_sibling_contract(
        wrapper_path.name, gate, "endfield.charinfo.secondary-dynamics-burst-wrapper.v1",
        "initialization_resolution_chain_closed_export_mapping_unresolved", require_burst=True,
    )
    direct = {
        385416: ("0x186762cc0", "collider_start_directcall"),
        385317: ("0x18675b0cc", "collider_end_directcall"),
    }
    for method_index, (expected_va, expected_role) in direct.items():
        row = rows.get(method_index)
        if row is None or row.get("va") != expected_va or row.get("role") != expected_role:
            raise ContractError(f"Burst wrapper contract identity drift for {method_index}: expected {expected_va}/{expected_role}")
    return wrapper_provenance


def build_contract(*, game_assembly: Path | None = DEFAULT_GAME_ASSEMBLY,
                   metadata: Path | None = DEFAULT_METADATA) -> dict[str, Any]:
    gate = _native_gate(game_assembly, metadata)
    wrapper_provenance = _validate_solver_identity_contract(gate)
    pe = _pe_exports(Path(gate["libBurstGenerated"]["path"]))
    rows = _body_rows(pe)
    hashes = [row["hash"] for row in rows]
    variant_prefixes = Counter()
    # The four named Burst initializer variants are useful sanity evidence,
    # but they are not kernel identities.
    for export in pe["exports"]:
        if export["name"].startswith("burst.initialize.externals."):
            variant_prefixes["externals"] += 1
        elif export["name"].startswith("burst.initialize.statics."):
            variant_prefixes["statics"] += 1
    spans = Counter(str(row["spanBytes"]) for row in rows)
    bodies = Counter(str(row["bodyBytes"]) for row in rows)
    targets = _target_candidates(pe, rows, gate)
    targets["simulationStartRange"]["semanticFingerprint"] = _simulation_semantic_fingerprint(pe, rows, gate)
    return {
        "schema": "endfield.charinfo.secondary-dynamics-burst-export.v1",
        "status": "secondary_dynamics_static_candidate_classification_unresolved_export_identity",
        "native_gate": gate,
        "pe": {
            "imageBase": f"0x{pe['imageBase']:x}",
            "exportDirectoryRva": f"0x{pe['exportDirectoryRva']:x}",
            "exportDirectorySize": pe["exportDirectorySize"],
            "totalNamedExportCount": len(pe["exports"]),
            "hashedExportCount": len(hashes),
            "hashedExportNamesSha256": hashlib.sha256("\n".join(sorted(hashes)).encode()).hexdigest(),
            "hashedRvaRange": {"first": f"0x{pe['hashed'][0]['rva']:x}", "last": f"0x{pe['hashed'][-1]['rva']:x}"},
            "initializerVariantCounts": dict(sorted(variant_prefixes.items())),
        },
        "functionBoundary": {"rule": "Capstone-decoded-instructions-through-first-real-ret", "spanBytesHistogram": dict(sorted(spans.items(), key=lambda item: int(item[0]))), "bodyBytesHistogram": dict(sorted(bodies.items(), key=lambda item: int(item[0])))},
        "targets": targets,
        "exports": rows,
        "contractComparison": {
            "solverStatic": _contract_snapshot("secondary_dynamics_solver_static_contract.json"),
            "innerLayout": _contract_snapshot("secondary_dynamics_inner_layout_contract.json"),
            "jobLayout": _contract_snapshot("secondary_dynamics_job_layout_contract.json"),
            "integrator": _contract_snapshot("secondary_dynamics_integrator_contract.json"),
            "burstWrapperProvenance": wrapper_provenance,
        },
        "unresolved": [
            "No exact 32-hex hash bytes or 16-byte hash values were found in GameAssembly.dll; static export-table analysis cannot join a managed BurstDirectCall to a hash.",
            "The candidate sets are ABI/function-shape evidence only. Runtime GetProcAddress plus a call-site/returned-pointer trace is required before publishing a hash-to-kernel mapping.",
            "The DLL export rows are intentionally not promoted to a solver implementation or a secondary-dynamics verification claim.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="verify the generated JSON without writing")
    args = parser.parse_args()
    try:
        result = build_contract(game_assembly=args.game_assembly, metadata=args.metadata)
        serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            matches = args.output.is_file() and args.output.read_text(encoding="utf-8") == serialized
            print(json.dumps({"status": result["status"], "matches": matches, "output": str(args.output)}))
            return 0 if matches else 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(json.dumps({"status": result["status"], "output": str(args.output)}))
        return 0
    except (OSError, ValueError, KeyError, ContractError) as exc:
        print(json.dumps({"status": "unavailable", "validationFailures": [str(exc)]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
