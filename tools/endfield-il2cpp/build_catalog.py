#!/usr/bin/env python3
"""Build an exact-build IL2CPP core type-surface catalog.

The metadata parser supplies definitions; the registration scanner supplies
the build-specific native tables.  Rows are never discarded: malformed or
unresolved relationships are retained with an explicit ``status``.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
METADATA_HELPER = ROOT / "tools/endfield-il2cpp/catalog_option_flow_metadata.py"
MAPPER_HELPER = ROOT / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py"


def load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_int(value: str | None) -> int | None:
    return int(value, 0) if value else None


def ptr(pe: Any, address: int, index: int, width: int = 8) -> int:
    entry = address + index * width if address and index >= 0 else 0
    raw = read_bytes(pe, entry, width)
    return struct.unpack_from("<Q", raw)[0] if raw is not None and width == 8 else 0


def valid_va(pe: Any, address: int) -> bool:
    if not address:
        return False
    try:
        return pe.file_offset_for_va(address)[0] is not None
    except (ValueError, struct.error):
        return False


def i32_at_va(pe: Any, address: int) -> int:
    offset, _section, _rva = pe.file_offset_for_va(address)
    if offset is None:
        raise ValueError(f"invalid VA 0x{address:x}")
    return struct.unpack_from("<i", pe.buf, offset)[0]


def read_bytes(pe: Any, address: int, size: int) -> bytes | None:
    if size < 0 or not valid_va(pe, address):
        return None
    offset, _section, _rva = pe.file_offset_for_va(address)
    if offset is None or offset + size > len(pe.buf):
        return None
    sections = getattr(pe, "sections", None)
    if sections:
        section = next((s for s in sections if s.get("rawPointer", 0) <= offset < s.get("rawPointer", 0) + s.get("rawSize", 0)), None)
        if section is None or offset + size > section["rawPointer"] + section["rawSize"]:
            return None
    return pe.buf[offset:offset + size]


def method_mapping_status(module: dict[str, Any] | None, metadata_count: int) -> tuple[str, str | None]:
    if module is None:
        return "unresolved", "missing-module"
    if module.get("methodPointerCount") != metadata_count:
        return "unresolved", "method-span-count-mismatch"
    return "resolved", None


def aggregate_status(types: list[dict[str, Any]], fields: list[dict[str, Any]], methods: list[dict[str, Any]], parameters: list[dict[str, Any]], images: list[dict[str, Any]]) -> dict[str, int]:
    return {"metadataTypes": len(types), "metadataImages": len(images), "metadataFields": len(fields),
            "metadataMethods": len(methods), "metadataParameters": len(parameters),
            "malformedTypes": sum(t["status"] != "resolved" for t in types),
            "malformedFields": sum(f["status"] != "resolved" for f in fields),
            "malformedMethods": sum(m["status"] != "resolved" for m in methods),
            "malformedParameters": sum(p["status"] != "resolved" for p in parameters),
            "malformedImages": sum(i["status"] != "resolved" for i in images),
            "malformedParameterRanges": sum(m.get("parameterRangeStatus") != "resolved" for m in methods),
            "unresolvedNativeLayouts": sum(t["nativeLayout"]["status"] != "resolved" for t in types)}


def catalog_status(coverage: dict[str, int], module_diagnostics: list[dict[str, Any]]) -> str:
    gap_keys = (
        "malformedTypes", "malformedFields", "malformedMethods",
        "malformedParameters", "malformedImages", "malformedParameterRanges",
        "unresolvedNativeLayouts",
    )
    return "complete_with_unresolved" if module_diagnostics or any(coverage[key] for key in gap_keys) else "complete"


def write_report(path: Path, report: dict[str, Any]) -> None:
    """Publish compact JSON atomically; never leave a partial catalog at *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise RuntimeError(f"refusing to reuse stale catalog staging file: {temporary}")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
        temporary.replace(path)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise


def status_for_range(start: int, count: int, total: int) -> str:
    # IL2CPP metadata uses -1 as the start sentinel for many empty ranges.
    # Preserve the raw start in the row, but do not classify the canonical
    # empty representation as malformed.
    if count == 0 and start == -1:
        return "resolved"
    if start < 0 or count < 0 or start > total or count > total - start:
        return "malformed"
    return "resolved"


def build(args: argparse.Namespace) -> dict[str, Any]:
    metadata_path = args.metadata.resolve()
    gameassembly_path = args.gameassembly.resolve()
    if not metadata_path.is_file() or not gameassembly_path.is_file():
        missing = [str(p) for p in (metadata_path, gameassembly_path) if not p.is_file()]
        raise RuntimeError("exact native inputs missing: " + ", ".join(missing))

    mdmod = load("endfield_catalog_metadata", METADATA_HELPER)
    mapper = load("endfield_catalog_mapper", MAPPER_HELPER)
    md = mdmod.Metadata(metadata_path)
    pe = mapper.PeImage(gameassembly_path)

    # Use the same mapper discovery primitives as generate_dummydll.py.  Keep
    # the complete image-set check here so this tool cannot accept a nearby
    # registration structure from another build.
    image_names = {md.string(image.name_index) for image in md.images}
    supplied_code = parse_int(args.code_registration)
    code_reg = supplied_code
    derived_candidates = mapper.find_code_registration_candidates(pe, image_names)
    if code_reg is None:
        candidates = derived_candidates
        if len(candidates) != 1:
            raise RuntimeError("CodeRegistration discovery was not unique: " +
                               ", ".join(f"0x{x:x}" for x in candidates))
        code_reg = candidates[0]
    modules = mapper.parse_codegen_modules(pe, code_reg)
    if {name.casefold() for name in modules} != {name.casefold() for name in image_names}:
        raise RuntimeError("CodeRegistration module set does not match metadata images")
    derived_metadata = mapper.find_metadata_registration(pe, code_reg)
    supplied_metadata = parse_int(args.metadata_registration)
    if supplied_code is not None and derived_candidates and code_reg not in derived_candidates:
        raise RuntimeError("supplied CodeRegistration does not match discovered candidate")
    if supplied_metadata is not None and derived_metadata is not None and supplied_metadata != derived_metadata:
        raise RuntimeError("supplied MetadataRegistration does not match derived registration")
    metadata_reg = supplied_metadata or derived_metadata
    if metadata_reg is None or not mapper.metadata_registration_is_plausible(pe, metadata_reg):
        raise RuntimeError("MetadataRegistration discovery failed pointer validation")
    registration = {"code": mapper.code_registration_summary(pe, code_reg),
                    "metadata": mapper.metadata_registration_summary(pe, metadata_reg),
                    "codeRegistrationSource": "supplied" if supplied_code is not None else "discovered",
                    "metadataRegistrationSource": "supplied" if supplied_metadata is not None else "derived"}
    reg_summary = mapper.metadata_registration_summary(pe, metadata_reg)
    offsets_va = int(reg_summary["fieldOffsets"], 16)
    sizes_va = int(reg_summary["typeDefinitionsSizes"], 16)
    type_count = int(reg_summary["fieldOffsetsCount"])
    size_count = int(reg_summary["typeDefinitionsSizesCount"])

    # Native method pointers are ordered by each codegen module's metadata
    # method span.  A missing/short span remains explicit on the method row.
    method_ranges = mapper.image_method_ranges(md)
    pointers_by_image, _ = mapper.build_pointer_indexes(pe, md, modules, method_ranges)
    methods_by_image: dict[str, list[int]] = {}
    module_diagnostics: list[dict[str, Any]] = []
    bad_modules: set[str] = set()
    for image_name, span in method_ranges.items():
        methods_by_image[image_name] = pointers_by_image.get(image_name, [])
        module = modules.get(image_name)
        mapping, reason = method_mapping_status(module, span.get("methodCount", 0))
        if mapping != "resolved":
            module_diagnostics.append({
                "image": image_name,
                "status": "unresolved" if module is None else "malformed",
                "reason": reason,
                "metadataMethodCount": span.get("methodCount", 0),
                "nativeMethodPointerCount": module["methodPointerCount"] if module is not None else None,
            })
            bad_modules.add(image_name.casefold())
    pointer_use_count: dict[int, int] = {}
    for pointers in methods_by_image.values():
        for value in pointers:
            if value:
                pointer_use_count[value] = pointer_use_count.get(value, 0) + 1

    def type_row(t: Any) -> dict[str, Any]:
        image_name = md.image_name_by_type_index.get(t.index, "")
        row_status = "resolved"
        issues: list[str] = []
        for start, count, total, label in (
            (t.field_start, t.field_count, len(md.fields), "fields"),
            (t.method_start, t.method_count, len(md.methods), "methods"),
            (t.interfaces_start, t.interfaces_count, md.sections["interfaces"].size // 4, "interfaces"),
            (t.nested_types_start, t.nested_type_count, md.sections["nestedTypes"].size // 4, "nestedTypes"),
        ):
            if status_for_range(start, count, total) != "resolved":
                row_status = "malformed"
                issues.append(label)
        native_layout: dict[str, Any] = {"status": "unresolved"}
        if t.index >= type_count or t.index >= size_count:
            native_layout["reason"] = "outside-registration-table"
        else:
            offsets_ptr = ptr(pe, offsets_va, t.index)
            size_ptr = ptr(pe, sizes_va, t.index)
            if not valid_va(pe, size_ptr):
                native_layout["reason"] = "null-registration-row"
            else:
                layout_field_count = t.field_count if status_for_range(t.field_start, t.field_count, len(md.fields)) == "resolved" else 0
                offsets_raw = read_bytes(pe, offsets_ptr, 4 * layout_field_count) if layout_field_count else b""
                size_raw = read_bytes(pe, size_ptr, 16)
                if (layout_field_count and offsets_raw is None) or size_raw is None:
                    native_layout["reason"] = "truncated-registration-row"
                else:
                    native_layout = {
                    "status": "resolved",
                    "fieldOffsets": list(struct.unpack("<" + "i" * layout_field_count, offsets_raw)) if layout_field_count else [],
                    "instanceSize": struct.unpack_from("<I", size_raw, 0)[0],
                    "nativeSize": struct.unpack_from("<I", size_raw, 4)[0],
                    "staticFieldsSize": struct.unpack_from("<I", size_raw, 8)[0],
                    "threadStaticFieldsSize": struct.unpack_from("<I", size_raw, 12)[0],
                    }
        field_end = t.field_start + t.field_count
        method_end = t.method_start + t.method_count
        field_indexes = range(t.field_start, field_end) if 0 <= t.field_start <= field_end <= len(md.fields) else range(max(0, t.field_start), min(len(md.fields), max(0, field_end)))
        method_indexes = range(t.method_start, method_end) if 0 <= t.method_start <= method_end <= len(md.methods) else range(max(0, t.method_start), min(len(md.methods), max(0, method_end)))
        fields = []
        for field_index in field_indexes:
            field = md.fields[field_index]
            fields.append({"index": field.index, "name": md.string(field.name_index),
                           "typeIndex": field.type_index,
                           "typeName": md.metadata_type_name(field.type_index),
                           "token": f"0x{field.token:08x}"})
        methods = []
        image_pointers = methods_by_image.get(image_name, [])
        span = method_ranges.get(image_name, {})
        for method_index in method_indexes:
            method = md.methods[method_index]
            slot = method.index - int(span.get("methodStart", -1))
            native = image_pointers[slot] if image_name.casefold() not in bad_modules and 0 <= slot < len(image_pointers) else 0
            pointer_status = "unresolved"
            if image_name.casefold() in bad_modules:
                pointer_status = "unresolved_module_mismatch"
            elif native:
                pointer_status = "shared_pointer" if pointer_use_count.get(native, 0) > 1 else "resolved"
            methods.append({"index": method.index, "name": md.string(method.name_index),
                            "token": f"0x{method.token:08x}", "flags": f"0x{method.flags:04x}",
                            "returnTypeIndex": method.return_type,
                            "returnTypeName": md.metadata_type_name(method.return_type),
                            "parameterCount": method.parameter_count,
                            "parameters": [{"name": md.string(p.name_index), "typeIndex": p.type_index,
                                             "typeName": md.metadata_type_name(p.type_index),
                                             "token": f"0x{p.token:08x}"}
                                            for p in (md.parameters[method.parameter_start:method.parameter_start + method.parameter_count]
                                                      if 0 <= method.parameter_start <= method.parameter_start + method.parameter_count <= len(md.parameters)
                                                      else md.parameters[max(0, method.parameter_start):min(len(md.parameters), max(0, method.parameter_start + method.parameter_count))])],
                            "parameterRangeStatus": status_for_range(method.parameter_start, method.parameter_count, len(md.parameters)),
                            "nativePointer": f"0x{native:x}" if native else None,
                            "status": pointer_status})
        row = {"index": t.index, "status": row_status, "issues": issues,
               "name": md.type_name(t), "namespace": md.type_namespace(t),
               "fullName": md.type_full_name(t), "image": image_name or None,
               "token": f"0x{t.token:08x}", "flags": f"0x{t.flags:08x}",
               "fieldRange": {"start": t.field_start, "count": t.field_count, "status": status_for_range(t.field_start, t.field_count, len(md.fields))},
               "methodRange": {"start": t.method_start, "count": t.method_count, "status": status_for_range(t.method_start, t.method_count, len(md.methods))},
               "parentIndex": t.parent_index, "declaringTypeIndex": t.declaring_type_index,
               "elementTypeIndex": t.element_type_index, "genericContainerIndex": t.generic_container_index,
               "interfaces": [md._i32(md.sections["interfaces"].offset + (t.interfaces_start + i) * 4)
                              for i in range(max(0, t.interfaces_count)) if 0 <= t.interfaces_start + i < md.sections["interfaces"].size // 4],
               "fields": fields, "methods": methods, "nativeLayout": native_layout}
        return row

    types = [type_row(t) for t in md.types]
    registered_type_count = int(reg_summary["typesCount"])
    top_fields = [{"index": f.index, "name": md.string(f.name_index), "typeIndex": f.type_index,
                   "typeName": md.metadata_type_name(f.type_index), "token": f"0x{f.token:08x}",
                   "status": "resolved" if 0 <= f.type_index < registered_type_count else "malformed"} for f in md.fields]
    top_parameters = [{"index": p.index, "name": md.string(p.name_index), "typeIndex": p.type_index,
                       "typeName": md.metadata_type_name(p.type_index), "token": f"0x{p.token:08x}",
                       "status": "resolved" if 0 <= p.type_index < registered_type_count else "malformed"} for p in md.parameters]
    top_methods = [{"index": m.index, "name": md.string(m.name_index), "declaringType": m.declaring_type,
                    "token": f"0x{m.token:08x}",
                    "parameterRangeStatus": status_for_range(m.parameter_start, m.parameter_count, len(md.parameters)),
                    "status": "resolved" if 0 <= m.declaring_type < len(md.types)
                    and 0 <= m.return_type < registered_type_count else "malformed"}
                   for m in md.methods]
    images = [{"index": image.index, "name": md.string(image.name_index),
               "assemblyIndex": image.assembly_index, "typeStart": image.type_start,
               "typeCount": image.type_count, "status": status_for_range(image.type_start, image.type_count, len(md.types))}
              for image in md.images]
    coverage = aggregate_status(types, top_fields, top_methods, top_parameters, images)
    return {"schema": "endfield-il2cpp-core-type-surface-v1", "scope": "core_metadata_type_surface",
            "status": catalog_status(coverage, module_diagnostics),
            "source": {"metadata": str(metadata_path), "metadataSha256": sha256(metadata_path),
                       "gameAssembly": str(gameassembly_path), "gameAssemblySha256": sha256(gameassembly_path)},
            "metadata": mdmod.catalog_metadata_summary(md),
            "registration": registration, "codegenModules": modules,
            "diagnostics": {"moduleMethodSpans": module_diagnostics,
                            "unhandledMetadataSections": ["events", "properties", "genericParameters", "genericContainers", "exportedTypeDefinitions"]},
            "images": images,
            "coverage": {**coverage, "resolvedTypes": sum(t["status"] == "resolved" for t in types),
                          "nativeLayoutResolved": sum(t["nativeLayout"]["status"] == "resolved" for t in types),
                          "methodRows": sum(len(t["methods"]) for t in types),
                          "fieldRows": sum(len(t["fields"]) for t in types)},
            "types": types, "fields": top_fields, "methods": top_methods, "parameters": top_parameters}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--code-registration")
    parser.add_argument("--metadata-registration")
    args = parser.parse_args()
    report = build(args)
    write_report(args.out, report)
    print(json.dumps(report["coverage"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
