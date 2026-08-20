#!/usr/bin/env python3
"""Recover the closed generic payloads used by the secondary-dynamics jobs.

This is deliberately a small, fail-closed evidence contract.  It uses the
pinned GameAssembly and metadata registrations for the generic IL2CPP bodies
and requires the pinned Burst DLL, but it does not pretend that a Burst
wrapper has been joined to one of the DLL's hashed exports.  That join remains
an explicit unresolved boundary.
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


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None
EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_LIB_BURST_SHA256 = "ee8702dd63dec2db7dc29d5bc23b8acd032f0e19a0daad5f69e6c45f9d3ceb99"
DEFAULT_OUTPUT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/secondary_dynamics_inner_layout_contract.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    """Raised when a pinned native evidence gate does not close."""


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load IL2CPP helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _helpers() -> tuple[Any, Any]:
    root = REPO_ROOT / "tools/endfield-il2cpp"
    return (_load("secondary_inner_metadata", root / "catalog_option_flow_metadata.py"),
            _load("secondary_inner_native", root / "map_body_targets_to_gameassembly.py"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _file(path: Path, digest: str | None = None) -> dict[str, Any]:
    return {"path": _path(path), "size": path.stat().st_size, "sha256": digest or _sha256(path)}


def _native_gate(game_assembly: Path | None, metadata: Path | None) -> dict[str, Any]:
    result = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256, EXPECTED_METADATA_SHA256,
        gameassembly=game_assembly, metadata=metadata,
    )
    if not result.validated:
        raise ContractError(f"common.check_installed_native_inputs [{result.status}]: {result.detail}")
    ga = Path(result.gameassembly)
    md = Path(result.metadata)
    burst = ga.parent / "Endfield_Data/Plugins/x86_64/lib_burst_generated.dll"
    if not burst.is_file():
        raise ContractError(f"missing pinned lib_burst_generated.dll: {burst}")
    burst_hash = _sha256(burst)
    if burst_hash != EXPECTED_LIB_BURST_SHA256:
        raise ContractError(f"lib_burst_generated.dll sha256 mismatch: {burst_hash}")
    return {"gameAssembly": _file(ga, result.gameassembly_sha256),
            "globalMetadata": _file(md, result.metadata_sha256),
            "libBurstGenerated": _file(burst, burst_hash)}


def _pointer(gi: dict[int, list[dict[str, Any]]], native: Any, method: int,
             type_index: int | None = None, type_name: str | None = None) -> int:
    rows = native.generic_body_candidates(gi, method)
    matches: list[int] = []
    for row in rows:
        if type_index is None:
            matches.append(int(row["methodPointerVa"], 16))
            continue
        if any(
            (class_inst.get("status") == "decoded"
             and class_inst.get("argumentCount") == 1
             and len(arguments) == 1
             and arguments[0].get("typeIndex") == type_index
             and (type_name is None or arguments[0].get("typeName") == type_name))
            for inst in row["instantiations"]
            for class_inst in [inst.get("classInstantiation", {})]
            for arguments in [class_inst.get("arguments", [])]
        ):
            matches.append(int(row["methodPointerVa"], 16))
    if len(matches) != 1:
        suffix = f" {type_name}" if type_name else ""
        raise ContractError(f"method {method} type {type_index}{suffix} resolves to {len(matches)} bodies")
    return matches[0]


def _evidence(pe: Any, pointer: int, name: str,
              patterns: tuple[tuple[str, bytes], ...], body_size: int,
              next_pointer: int | None) -> dict[str, Any]:
    # Bound the probe at the next known IL2CPP method pointer.  A fixed 256
    # byte read can otherwise match bytes in the following function.
    if body_size <= 0 or body_size > 256:
        raise ContractError(f"{name} has no bounded method span")
    body = pe.bytes_at_va(pointer, body_size)
    if len(body) != body_size:
        raise ContractError(f"{name} bounded probe is truncated")
    found: dict[str, str] = {}
    for label, pattern in patterns:
        offset = body.find(pattern)
        if offset < 0:
            raise ContractError(f"{name} 0x{pointer:x} lacks {label} pattern")
        found[label] = f"0x{offset:x}"
    file_offset, section, _ = pe.file_offset_for_va(pointer)
    if file_offset is None:
        raise ContractError(f"generic body 0x{pointer:x} is outside GameAssembly")
    return {"methodPointerVa": f"0x{pointer:x}", "fileOffset": f"0x{file_offset:x}",
            "section": section, "probeBytes": len(body),
            "nextMethodPointerVa": f"0x{next_pointer:x}" if next_pointer else None,
            "probeSha256": hashlib.sha256(body).hexdigest(), "patterns": found}


def _exports(path: Path) -> dict[str, Any]:
    # Parse IMAGE_EXPORT_DIRECTORY.  Scanning the whole DLL for 32-hex ASCII
    # strings would count arbitrary data and is not evidence of an export.
    data = path.read_bytes()
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ContractError("pinned lib_burst_generated.dll is not a PE image")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset + 24 > len(data) or data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ContractError("pinned lib_burst_generated.dll has no PE signature")
    coff = pe_offset + 4
    section_count = struct.unpack_from("<H", data, coff + 2)[0]
    optional_size = struct.unpack_from("<H", data, coff + 16)[0]
    optional = coff + 20
    if optional + optional_size > len(data) or struct.unpack_from("<H", data, optional)[0] != 0x20B:
        raise ContractError("pinned lib_burst_generated.dll is not PE32+")
    export_rva, export_size = struct.unpack_from("<II", data, optional + 112)
    if not export_rva or export_size < 40:
        raise ContractError("pinned lib_burst_generated.dll has no export directory")
    section_table = optional + optional_size
    sections: list[tuple[int, int, int]] = []
    for index in range(section_count):
        section = section_table + index * 40
        if section + 40 > len(data):
            raise ContractError("truncated PE section table")
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from("<IIII", data, section + 8)
        sections.append((virtual_address, max(virtual_size, raw_size), raw_pointer))

    def rva_offset(rva: int, size: int = 1) -> int:
        for virtual_address, section_size, raw_pointer in sections:
            if virtual_address <= rva and rva + size <= virtual_address + section_size:
                offset = raw_pointer + (rva - virtual_address)
                if 0 <= offset <= len(data) - size:
                    return offset
        raise ContractError(f"export RVA 0x{rva:x} is outside PE sections")

    directory = rva_offset(export_rva, 40)
    (characteristics, timestamp, major, minor, name_rva, ordinal_base,
     function_count, name_count, functions_rva, names_rva,
     ordinals_rva) = struct.unpack_from("<IIHHIIIIIII", data, directory)
    del characteristics, timestamp, major, minor, name_rva, ordinal_base, functions_rva, ordinals_rva
    if name_count > function_count or name_count > 1_000_000:
        raise ContractError("invalid PE export name/function counts")
    names: list[bytes] = []
    for index in range(name_count):
        name_pointer = struct.unpack_from("<I", data, rva_offset(names_rva + index * 4, 4))[0]
        name_offset = rva_offset(name_pointer)
        end = data.find(b"\0", name_offset)
        if end < 0:
            raise ContractError("unterminated PE export name")
        name = data[name_offset:end]
        if re.fullmatch(rb"[0-9a-f]{32}", name):
            names.append(name)
    names = sorted(set(names))
    if not names:
        raise ContractError("pinned lib_burst_generated.dll has no hashed export names")
    return {"hashedExportCount": len(names),
            "hashedExportNamesSha256": hashlib.sha256(b"\n".join(names)).hexdigest(),
            "mappingStatus": "unresolved_wrapper_to_hashed_export"}


def build_contract(*, game_assembly: Path | None = DEFAULT_GAME_ASSEMBLY,
                   metadata: Path | None = DEFAULT_METADATA) -> dict[str, Any]:
    gate = _native_gate(game_assembly, metadata)
    catalog, native = _helpers()
    md = catalog.Metadata(Path(gate["globalMetadata"]["path"]))
    pe = native.PeImage(Path(gate["gameAssembly"]["path"]))
    names = {50690: "Unity.Collections.NativeArray`1", 60806: "Unity.Collections.NativeReference`1"}
    for index, expected in names.items():
        if md.type_full_name(md.types[index]) != expected:
            raise ContractError(f"generic definition {index} name drift")
    image_names = {md.string(image.name_index) for image in md.images}
    code_registration = native.find_code_registration(pe, image_names)
    metadata_registration = native.find_metadata_registration(pe, code_registration)
    if code_registration != 0x18B9217D0 or metadata_registration != 0x18B921C30:
        raise ContractError("IL2CPP registration addresses drifted")
    generic = native.build_generic_method_index(pe, md, code_registration, metadata_registration)
    generic_type_index = 148327
    generic_type_name = "System.Int32"
    if md.metadata_type_name(generic_type_index) != generic_type_name:
        raise ContractError(f"generic argument {generic_type_index} name drift")
    modules = native.parse_codegen_modules(pe, code_registration)
    ranges = native.image_method_ranges(md)
    pointers_by_image, _ = native.build_pointer_indexes(pe, md, modules, ranges)
    sorted_pointers = sorted({pointer for pointers in pointers_by_image.values() for pointer in pointers if pointer} | set(generic))

    def body_evidence(pointer: int, name: str, patterns: tuple[tuple[str, bytes], ...]) -> dict[str, Any]:
        body_size, next_pointer = native.estimate_scan_size(pointer, sorted_pointers, 256)
        if next_pointer is None:
            raise ContractError(f"{name} 0x{pointer:x} has no next method boundary")
        return _evidence(pe, pointer, name, patterns, body_size, next_pointer)

    # The Allocate body materializes all three NativeArray slots.  The two
    # accessor bodies independently establish the pointer and length offsets.
    na_allocate = _pointer(generic, native, 401946, generic_type_index, generic_type_name)
    na_length = _pointer(generic, native, 401947, generic_type_index, generic_type_name)
    na_created = _pointer(generic, native, 401950, generic_type_index, generic_type_name)
    nr_allocate = _pointer(generic, native, 477517, generic_type_index, generic_type_name)
    nr_value = _pointer(generic, native, 477518, generic_type_index, generic_type_name)
    nr_set = _pointer(generic, native, 477519, generic_type_index, generic_type_name)
    nr_created = _pointer(generic, native, 477520, generic_type_index, generic_type_name)
    native_array = {
        "definitionTypeIndex": 50690, "nativeSizeBytes": None,
        "nativeSizeEvidence": {"status": "lower_bound_only", "lowerBoundBytes": 16,
                                "reason": "Allocate writes the three recovered fields through byte 0x0f, but no closed generic type-size record proves that trailing padding is absent."},
        "fields": {"m_Buffer": {"offset": "0x0", "widthBytes": 8},
                   "m_Length": {"offset": "0x8", "widthBytes": 4},
                   "m_AllocatorLabel": {"offset": "0xc", "widthBytes": 4}},
        "evidence": {
            "allocate": body_evidence(na_allocate, "NativeArray.Allocate", (
                ("zeroes_16_byte_result", b"\x0f\x11\x03"),
                ("allocator_at_plus_c", b"\x89\x7b\x0c"),
                ("length_at_plus_8", b"\x44\x89\x73\x08"),
                ("buffer_at_plus_0", b"\x48\x89\x03"))),
            "get_Length": body_evidence(na_length, "NativeArray.get_Length",
                                     (("length_load_plus_8", b"\x8b\x41\x08"),)),
            "get_IsCreated": body_evidence(na_created, "NativeArray.get_IsCreated",
                                        (("buffer_test_plus_0", b"\x48\x83\x39\x00"),)),
        },
    }
    native_reference = {
        "definitionTypeIndex": 60806, "nativeSizeBytes": None,
        "nativeSizeEvidence": {"status": "lower_bound_only", "lowerBoundBytes": 12,
                                "reason": "Allocate writes the recovered allocator field through byte 0x0b; neither this body nor a closed generic type-size record proves bytes 0x0c-0x0f or the absence of trailing padding."},
        "fields": {"m_Data": {"offset": "0x0", "widthBytes": 8},
                   "m_AllocatorLabel": {"offset": "0x8", "widthBytes": 4}},
        "evidence": {
            "allocate": body_evidence(nr_allocate, "NativeReference.Allocate", (
                ("allocator_at_plus_8", b"\x89\x5f\x08"),
                ("data_at_plus_0", b"\x48\x89\x07"))),
            "get_Value": body_evidence(nr_value, "NativeReference.get_Value",
                                    (("data_deref_plus_0", b"\x48\x8b\x01\x8b\x00"),)),
            "set_Value": body_evidence(nr_set, "NativeReference.set_Value",
                                    (("data_deref_plus_0", b"\x48\x8b\x01\x89\x10"),)),
            "get_IsCreated": body_evidence(nr_created, "NativeReference.get_IsCreated",
                                        (("data_test_plus_0", b"\x48\x83\x39\x00"),)),
        },
    }
    return {
        "schema": "endfield.charinfo.secondary-dynamics-inner-layout.v1",
        "status": "inner_payload_offsets_closed_size_unresolved_burst_mapping_unresolved",
        "inner_payload_layout_recovered": False,
        "inner_payload_offsets_recovered": True,
        "job_payload_layout_recovered": False,
        "secondary_dynamics_verified": False,
        "native_gate": gate,
        "metadataRegistration": {"codeRegistrationVa": f"0x{code_registration:x}",
                                  "metadataRegistrationVa": f"0x{metadata_registration:x}"},
        "nativeArray": native_array,
        "nativeReference": native_reference,
        "burstExports": _exports(Path(gate["libBurstGenerated"]["path"])),
        "unresolved": [
            "BurstDirectCall GetFunctionPointer/Discard wrappers are not statically joined to a specific hashed lib_burst_generated.dll export.",
            "No Execute/UnsafeDo semantic or solver contract is claimed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
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
