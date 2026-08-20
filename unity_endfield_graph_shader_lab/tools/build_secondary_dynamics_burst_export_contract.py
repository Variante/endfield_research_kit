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
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any


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
    for index in range(section_count):
        row = table + index * 40
        if row + 40 > len(data):
            raise ContractError("truncated PE section table")
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
            "<IIII", data, row + 8
        )
        sections.append((virtual_address, max(virtual_size, raw_size), raw_pointer))

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
    del characteristics, timestamp, major, minor, name_rva, ordinal_base
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
        exports.append({"name": name, "rva": function_rva})
    exports.sort(key=lambda row: (row["rva"], row["name"]))
    if not exports:
        raise ContractError("pinned lib_burst_generated.dll has no named exports")
    hashed = [row for row in exports if re.fullmatch(r"[0-9a-f]{32}", row["name"])]
    if len(hashed) != 628:
        raise ContractError(f"expected 628 hashed exports, found {len(hashed)}")
    return {
        "data": data,
        "sections": sections,
        "imageBase": image_base,
        "exportDirectoryRva": export_rva,
        "exportDirectorySize": export_size,
        "exports": exports,
        "hashed": hashed,
    }


def _stack_writes(body: bytes) -> list[dict[str, Any]]:
    """Recover the small set of x64 stack-store encodings used by wrappers."""
    rows: list[dict[str, Any]] = []
    index = 0
    while index < len(body):
        # mov qword ptr [rsp+disp8], r64
        if index + 4 < len(body) and body[index] in (0x48, 0x4C) and body[index + 1] == 0x89 and (body[index + 2] & 0xC7) == 0x44 and body[index + 3] == 0x24:
            rows.append({"offset": body[index + 4], "widthBytes": 8})
            index += 5
            continue
        if index + 8 <= len(body) and body[index] in (0x48, 0x4C) and body[index + 1] == 0x89 and (body[index + 2] & 0xC7) == 0x84 and body[index + 3] == 0x24:
            rows.append({"offset": int.from_bytes(body[index + 4:index + 8], "little"), "widthBytes": 8})
            index += 8
            continue
        # mov dword ptr [rsp+disp8], r32
        if index + 3 < len(body) and body[index] == 0x89 and (body[index + 1] & 0xC7) == 0x44 and body[index + 2] == 0x24:
            rows.append({"offset": body[index + 3], "widthBytes": 4})
            index += 4
            continue
        if index + 7 <= len(body) and body[index] == 0x89 and (body[index + 1] & 0xC7) == 0x84 and body[index + 2] == 0x24:
            rows.append({"offset": int.from_bytes(body[index + 3:index + 7], "little"), "widthBytes": 4})
            index += 7
            continue
        # movss dword ptr [rsp+disp8], xmm
        if index + 5 < len(body) and body[index:index + 3] == b"\xf3\x0f\x11" and (body[index + 3] & 0xC7) == 0x44 and body[index + 4] == 0x24:
            rows.append({"offset": body[index + 5], "widthBytes": 4, "kind": "xmm"})
            index += 6
            continue
        if index + 9 <= len(body) and body[index:index + 3] == b"\xf3\x0f\x11" and (body[index + 3] & 0xC7) == 0x84 and body[index + 4] == 0x24:
            rows.append({"offset": int.from_bytes(body[index + 5:index + 9], "little"), "widthBytes": 4, "kind": "xmm"})
            index += 9
            continue
        index += 1
    # The byte patterns above can only occur at instruction starts in these
    # generated wrappers; sorting makes the report independent of scan order.
    return sorted(rows, key=lambda row: (row["offset"], row["widthBytes"], row.get("kind", "gpr")))


def _stack_load_registers(body: bytes) -> list[str]:
    """Decode mov r64,[rbp+disp8] enough to detect incoming-GPR clobbers."""
    names = ["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
             "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]
    result: list[str] = []
    for index in range(max(0, len(body) - 3)):
        rex = body[index]
        if rex not in (0x48, 0x4C) or body[index + 1] != 0x8B:
            continue
        modrm = body[index + 2]
        if (modrm >> 6) != 1 or (modrm & 7) != 5:
            continue
        reg = ((modrm >> 3) & 7) + (8 if rex & 4 else 0)
        result.append(names[reg])
    return result


def _xmm_stack_load_count(body: bytes) -> int:
    count = 0
    for index in range(max(0, len(body) - 4)):
        if body[index:index + 3] != b"\xf3\x0f\x10":
            continue
        modrm = body[index + 3]
        if (modrm & 7) == 5 and (modrm >> 6) in (1, 2):
            count += 1
    return count


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
        ret = code.find(b"\xC3")
        body = code[:ret + 1] if ret >= 0 else code
        stores = _stack_writes(body)
        loads = _stack_load_registers(body)
        rows.append({
            "hash": export["name"],
            "rva": f"0x{export['rva']:x}",
            "fileOffset": f"0x{file_offset:x}",
            "spanBytes": span,
            "bodyBytes": len(body),
            "bodySha256": hashlib.sha256(body).hexdigest(),
            "retBoundary": "first_ret" if ret >= 0 else "span_end",
            "stackWrites": stores,
            "stackWriteOffsets": [f"0x{row['offset']:x}" for row in stores],
            "stackWriteWidths": [row["widthBytes"] for row in stores],
            "stackLoadRegisterDestinations": loads,
            "incomingGprClobbers": sorted(set(loads) & {"rcx", "rdx", "r8", "r9"}),
            "xmmStackLoadCount": _xmm_stack_load_count(body),
            "indirectRipCallCount": body.count(b"\xff\x15"),
        })
    return rows


def _target_candidates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_hash = {row["hash"]: row for row in rows}
    stores = lambda row: [(int(offset, 16), width) for offset, width in zip(row["stackWriteOffsets"], row["stackWriteWidths"])]
    simulation_shape = lambda row: len(stores(row)) == 25 and stores(row)[0][0] == 0x20 and stores(row)[-1][0] == 0xE0 and row["xmmStackLoadCount"] == 1
    sim_all = [row for row in rows if simulation_shape(row)]
    sim_qword = [row for row in sim_all if stores(row)[-1][1] == 8]
    collider_shape = lambda row: len(stores(row)) == 13 and stores(row)[0][0] == 0x20 and stores(row)[-1][0] == 0x80 and not row["incomingGprClobbers"]
    collider_all = [row for row in rows if collider_shape(row)]
    collider_dword = [row for row in collider_all if stores(row)[-1][1] == 4]
    end_shape = lambda row: stores(row) == [(0x20, 8), (0x28, 8)] and not row["incomingGprClobbers"]
    end_all = [row for row in rows if len(stores(row)) == 2 and stores(row)[0][0] == 0x20 and stores(row)[1][0] == 0x28 and stores(row)[0][1] == 8 and stores(row)[1][1] == 8]
    end_preserved = [row for row in end_all if not row["incomingGprClobbers"]]
    def brief(row: dict[str, Any]) -> dict[str, Any]:
        return {key: row[key] for key in ("hash", "rva", "spanBytes", "bodyBytes", "bodySha256", "stackWriteOffsets", "stackWriteWidths", "incomingGprClobbers")}
    return {
        "simulationStartRange": {
            "managedMethodIndex": 385542,
            "directInvokeMethodIndex": 385570,
            "directInvokeVa": "0x1867775fc",
            "parameterContract": {"parameterCount": 29, "leadingSingleCount": 5, "nativeArrayCount": 24, "lastParameter": "lengthPtr NativeArray<int>"},
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
            "parameterContract": {"parameterCount": 6, "nativeArrayCount": 6, "stackNativeArrayCount": 2},
            "status": "bounded_candidate_set" if len(end_preserved) > 1 else "unique_abi_candidate_identity_unresolved",
            "candidates": [brief(row) for row in end_preserved],
            "nearCandidatesExcluded": [brief(row) for row in end_all if row not in end_preserved],
            "exclusionReason": "09829f... loads the second stack argument into rdx and 1adf3a... into r9, clobbering incoming target GPRs; 89666f... uses displaced stack slots. The surviving r10 forms preserve rcx/rdx/r8/r9.",
        },
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


def build_contract(*, game_assembly: Path | None = DEFAULT_GAME_ASSEMBLY,
                   metadata: Path | None = DEFAULT_METADATA) -> dict[str, Any]:
    gate = _native_gate(game_assembly, metadata)
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
        "functionBoundary": {"rule": "first_ret_after_hashed_export_rva", "spanBytesHistogram": dict(sorted(spans.items(), key=lambda item: int(item[0]))), "bodyBytesHistogram": dict(sorted(bodies.items(), key=lambda item: int(item[0])))},
        "targets": _target_candidates(rows),
        "exports": rows,
        "contractComparison": {
            "solverStatic": _contract_snapshot("secondary_dynamics_solver_static_contract.json"),
            "innerLayout": _contract_snapshot("secondary_dynamics_inner_layout_contract.json"),
            "jobLayout": _contract_snapshot("secondary_dynamics_job_layout_contract.json"),
            "integrator": _contract_snapshot("secondary_dynamics_integrator_contract.json"),
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
