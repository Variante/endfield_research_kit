#!/usr/bin/env python3
"""Audit native producers and consumers of an installed managed value carrier.

The scanner is deliberately type/field driven.  A caller supplies one managed
carrier type and optional focus fields; the implementation derives current
runtime offsets, methods whose signatures carry the type, nested object paths,
native pointers, direct callsites, and stack-local initializers from the
installed IL2CPP metadata and GameAssembly.  Content ids, Story keys, mission
names, OCR, and manual overrides are never inputs.

This is a bounded static audit.  Direct AOT calls and decoded field accesses are
reported exactly; virtual/interface dispatch, reflection, XLua construction,
and live server values remain explicit boundaries.
"""

from __future__ import annotations

import argparse
import bisect
import importlib.util
import json
import re
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]
if __package__ == "scripts.story_recovery.native_carriers":
    from ...common import (
        md_escape,
        resolve_installed_game_data_root,
        sha256_file,
        write_report_json,
        write_text_if_changed,
    )
elif __package__ == "story_recovery.native_carriers":
    from common import (
        md_escape,
        resolve_installed_game_data_root,
        sha256_file,
        write_report_json,
        write_text_if_changed,
    )
else:  # pragma: no cover - invalid embedding identity
    raise ImportError(f"unsupported package identity: {__package__!r}")


MAPPER_PATH = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
CATALOG_PATH = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
DEFAULT_GAME_ROOT = resolve_installed_game_data_root()
DEFAULT_GAME_ASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
DEFAULT_JSON = ROOT / "reports" / "story" / "recovery" / "native_value_carrier_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "story" / "recovery" / "native_value_carrier_audit.md"
MAX_METHOD_BYTES = 0x10000
MAX_CONTAINER_DEPTH = 2


class AuditError(RuntimeError):
    """Raised when original inputs cannot produce a bounded carrier audit."""


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuditError(f"cannot load required helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module




def source_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path.resolve())


def parse_hex(value: str | int | None) -> int:
    if isinstance(value, int):
        return value
    return int(str(value or "0"), 0)


def signed_hex(value: int) -> str:
    return f"-0x{-value:x}" if value < 0 else f"+0x{value:x}"


class RuntimeTypes:
    """Resolve installed Il2CppType rows and instance layouts with caching."""

    def __init__(self, pe: Any, metadata: Any, mapper: Any, registration: int) -> None:
        self.pe = pe
        self.metadata = metadata
        self.mapper = mapper
        self.registration = registration
        self.summary = mapper.metadata_registration_summary(pe, registration)
        self.types_va = int(self.summary["types"], 16)
        self.field_offsets_va = int(self.summary["fieldOffsets"], 16)
        self.sizes_va = int(self.summary["typeDefinitionsSizes"], 16)
        self._name_cache: dict[int, str] = {}
        self._layout_cache: dict[int, list[dict[str, Any]]] = {}

    def type_pointer(self, metadata_type_index: int) -> int:
        count = int(self.summary["typesCount"])
        if not 0 <= metadata_type_index < count:
            return 0
        return self.pe.u64_at_va(self.types_va + metadata_type_index * 8)

    def type_name(self, metadata_type_index: int) -> str:
        cached = self._name_cache.get(metadata_type_index)
        if cached is not None:
            return cached
        pointer = self.type_pointer(metadata_type_index)
        if not pointer:
            name = f"<type-index:{metadata_type_index}>"
        else:
            offset, _section, _rva = self.pe.file_offset_for_va(pointer)
            if offset is None:
                name = f"<type-va:0x{pointer:x}>"
            else:
                data = struct.unpack_from("<Q", self.pe.buf, offset)[0]
                bits = struct.unpack_from("<I", self.pe.buf, offset + 8)[0]
                kind = (bits >> 16) & 0xFF
                if kind in {0x11, 0x12} and 0 <= data < len(self.metadata.types):
                    name = self.metadata.type_full_name(self.metadata.types[data])
                else:
                    # The mapper's runtime decoder handles generic instances,
                    # arrays, pointers, and primitive types.
                    name = _runtime_type_name(
                        self.pe,
                        self.metadata,
                        pointer,
                    )
        self._name_cache[metadata_type_index] = name
        return name

    def layout(self, type_index: int) -> list[dict[str, Any]]:
        cached = self._layout_cache.get(type_index)
        if cached is not None:
            return cached
        count = int(self.summary["fieldOffsetsCount"])
        if not 0 <= type_index < count:
            raise AuditError(f"type {type_index} outside runtime field-offset table")
        offsets_va = self.pe.u64_at_va(self.field_offsets_va + type_index * 8)
        if not offsets_va:
            raise AuditError(f"type {type_index} has no runtime field-offset row")
        type_def = self.metadata.types[type_index]
        sizes = self.size(type_index)
        boxed_header = (
            sizes["instanceSize"] - sizes["nativeSize"]
            if 0 < sizes["nativeSize"] < 0x80000000
            and sizes["instanceSize"] - sizes["nativeSize"] == 0x10
            else 0
        )
        rows = []
        for index, field in enumerate(self.metadata.fields_for(type_def)):
            rows.append({
                "name": self.metadata.string(field.name_index),
                "token": f"0x{field.token:08x}",
                # MetadataRegistration stores boxed offsets for value types.
                # Normalize those back to their unboxed/native offsets so the
                # same path matcher works for value parameters and class fields.
                "offset": self.pe.u32_at_va(offsets_va + index * 4) - boxed_header,
                "typeIndex": field.type_index,
                "type": self.type_name(field.type_index),
            })
        self._layout_cache[type_index] = rows
        return rows

    def size(self, type_index: int) -> dict[str, int]:
        row_va = self.pe.u64_at_va(self.sizes_va + type_index * 8)
        if not row_va:
            raise AuditError(f"type {type_index} has no runtime size row")
        return {
            "instanceSize": self.pe.u32_at_va(row_va),
            "nativeSize": self.pe.u32_at_va(row_va + 4),
        }


RUNTIME_PRIMITIVES = {
    0x01: "void", 0x02: "bool", 0x03: "char", 0x04: "sbyte",
    0x05: "byte", 0x06: "short", 0x07: "ushort", 0x08: "int",
    0x09: "uint", 0x0A: "long", 0x0B: "ulong", 0x0C: "float",
    0x0D: "double", 0x0E: "string", 0x18: "nint", 0x19: "nuint",
    0x1C: "object",
}


def _runtime_type_name(
    pe: Any,
    metadata: Any,
    type_va: int,
    *,
    depth: int = 0,
    seen: frozenset[int] = frozenset(),
) -> str:
    if depth > 10 or type_va in seen:
        return "<recursive-runtime-type>"
    offset, _section, _rva = pe.file_offset_for_va(type_va)
    if offset is None:
        return f"<type-va:0x{type_va:x}>"
    data = struct.unpack_from("<Q", pe.buf, offset)[0]
    bits = struct.unpack_from("<I", pe.buf, offset + 8)[0]
    kind = (bits >> 16) & 0xFF
    if kind in RUNTIME_PRIMITIVES:
        return RUNTIME_PRIMITIVES[kind]
    if kind in {0x11, 0x12}:
        return (
            metadata.type_full_name(metadata.types[data])
            if 0 <= data < len(metadata.types)
            else f"<typedef:{data}>"
        )
    if kind == 0x0F:
        return _runtime_type_name(
            pe, metadata, data, depth=depth + 1, seen=seen | {type_va}
        ) + "*"
    if kind == 0x1D:
        return _runtime_type_name(
            pe, metadata, data, depth=depth + 1, seen=seen | {type_va}
        ) + "[]"
    if kind == 0x15:
        generic_offset, _section, _rva = pe.file_offset_for_va(data)
        if generic_offset is None:
            return f"<generic:0x{data:x}>"
        definition_va, class_inst_va = struct.unpack_from("<QQ", pe.buf, generic_offset)
        definition = _runtime_type_name(
            pe, metadata, definition_va, depth=depth + 1, seen=seen | {type_va}
        )
        if not class_inst_va:
            return definition
        count = pe.u32_at_va(class_inst_va)
        argv = pe.u64_at_va(class_inst_va + 8)
        if count > 64:
            return f"{definition}<invalid-argc:{count}>"
        args = [
            _runtime_type_name(
                pe,
                metadata,
                pe.u64_at_va(argv + index * 8),
                depth=depth + 1,
                seen=seen | {type_va},
            )
            for index in range(count)
        ]
        return f"{definition}<{','.join(args)}>"
    return f"<runtime-type:0x{kind:x}>"


def mapped_method_row(
    metadata: Any,
    catalog: Any,
    runtime: RuntimeTypes,
    method_index: int,
    owner: str,
) -> dict[str, Any]:
    method = metadata.methods[method_index]
    row = catalog.method_row(metadata, method)
    row["methodIndex"] = method_index
    row["method"] = row.pop("name")
    row["type"] = owner
    for parameter in row.get("parameterDetails") or []:
        parameter["typeName"] = runtime.type_name(int(parameter["typeIndex"]))
    row["returnTypeName"] = runtime.type_name(int(row["returnTypeIndex"]))
    return row


def build_pointer_index(
    pe: Any,
    metadata: Any,
    mapper: Any,
) -> tuple[list[int], dict[int, list[dict[str, Any]]], dict[int, list[int]]]:
    modules = mapper.parse_codegen_modules(pe, mapper.DEFAULT_CODE_REGISTRATION)
    ranges = mapper.image_method_ranges(metadata)
    _by_image, methods_by_pointer = mapper.build_pointer_indexes(
        pe, metadata, modules, ranges
    )
    registration = mapper.find_metadata_registration(pe, mapper.DEFAULT_CODE_REGISTRATION)
    if registration is None:
        raise AuditError("could not derive MetadataRegistration")
    for pointer, aliases in mapper.build_generic_method_index(
        pe,
        metadata,
        mapper.DEFAULT_CODE_REGISTRATION,
        registration,
    ).items():
        methods_by_pointer.setdefault(pointer, aliases)
    pointers_by_method: dict[int, list[int]] = defaultdict(list)
    for pointer, aliases in methods_by_pointer.items():
        for alias in aliases:
            method_index = alias.get("methodIndex")
            if method_index is not None and pointer not in pointers_by_method[int(method_index)]:
                pointers_by_method[int(method_index)].append(pointer)
    return sorted(methods_by_pointer), methods_by_pointer, pointers_by_method


def method_body(pe: Any, pointers: list[int], pointer: int) -> bytes:
    next_index = bisect.bisect_right(pointers, pointer)
    end = pointers[next_index] if next_index < len(pointers) else pointer + MAX_METHOD_BYTES
    return pe.bytes_at_va(pointer, min(max(0, end - pointer), MAX_METHOD_BYTES))


def field_width(instruction: dict[str, Any]) -> int:
    text = str(instruction.get("text") or "")
    opcode = text.split(" ", 1)[0]
    if opcode in {"movaps", "movups", "movdqu"}:
        return 16
    if opcode == "movsd":
        return 8
    source = text.rsplit(", ", 1)[-1]
    if re.fullmatch(r"(?:r(?:ax|bx|cx|dx|si|di|sp|bp)|r(?:8|9|1[0-5]))", source):
        return 8
    if re.fullmatch(r"(?:e(?:ax|bx|cx|dx|si|di|sp|bp)|r(?:8|9|1[0-5])d)", source):
        return 4
    if re.fullmatch(r"(?:[abcd]l|[sd]il|[sb]pl|r(?:8|9|1[0-5])b)", source):
        return 1
    raw = bytes.fromhex(str(instruction.get("bytes") or ""))
    if raw and raw[0] & 0xF0 == 0x40:
        return 8 if raw[0] & 0x08 else 4
    return 4


def instruction_zero_sources(mapper: Any, instructions: list[dict[str, Any]]) -> dict[int, bool]:
    """Track simple constant-zero register provenance at every instruction."""
    zero_registers: set[str] = set()
    result: dict[int, bool] = {}
    for instruction in instructions:
        text = str(instruction.get("text") or "")
        source = text.rsplit(", ", 1)[-1] if ", " in text else ""
        canonical_source = mapper.canonical_register(source)
        result[int(instruction.get("offset") or 0)] = (
            source in {"0", "0x0"} or canonical_source in zero_registers
        )
        write = instruction.get("write") or {}
        destination = mapper.canonical_register(str(write.get("register") or ""))
        if not destination:
            continue
        value = str(write.get("value") or "")
        canonical_value = mapper.canonical_register(value)
        if value in {"0", "0x0"} or canonical_value in zero_registers:
            zero_registers.add(destination)
        else:
            zero_registers.discard(destination)
    return result


def origin_parts(origin: str, root: str) -> list[int] | None:
    if origin == root:
        return []
    if not origin.startswith(root):
        return None
    suffix = origin[len(root):]
    parts = re.findall(r"([+-])0x([0-9a-f]+)", suffix)
    if not parts or "".join(f"{sign}0x{digits}" for sign, digits in parts) != suffix:
        return None
    return [int(digits, 16) * (-1 if sign == "-" else 1) for sign, digits in parts]


def access_overlaps_path(
    origin: str,
    root: str,
    path: list[int],
    width: int,
    field_width_bytes: int,
) -> bool:
    parts = origin_parts(origin, root)
    if parts is None or not path or len(parts) != len(path):
        return False
    if parts[:-1] != path[:-1]:
        return False
    access_start = parts[-1]
    field_start = path[-1]
    return access_start < field_start + field_width_bytes and field_start < access_start + width


def scalar_field_width(field_type: str, native_size: int, offset: int, next_offset: int) -> int:
    fixed = {
        "bool": 1, "byte": 1, "sbyte": 1, "char": 2, "short": 2,
        "ushort": 2, "int": 4, "uint": 4, "float": 4, "long": 8,
        "ulong": 8, "double": 8, "nint": 8, "nuint": 8,
        "System.Boolean": 1, "System.Byte": 1, "System.SByte": 1,
        "System.Int16": 2, "System.UInt16": 2, "System.Int32": 4,
        "System.UInt32": 4, "System.Single": 4, "System.Int64": 8,
        "System.UInt64": 8, "System.Double": 8,
    }
    if field_type in fixed:
        return fixed[field_type]
    return max(1, min(8, (next_offset if next_offset > offset else native_size) - offset))


def container_paths(
    metadata: Any,
    runtime: RuntimeTypes,
    carrier_type: str,
    *,
    max_depth: int,
) -> dict[int, list[dict[str, Any]]]:
    """Find instance-field paths that reach the carrier without name allowlists."""
    target_names = {carrier_type}
    type_index_by_name = {
        metadata.type_full_name(type_def): type_def.index for type_def in metadata.types
    }
    paths_by_type: dict[int, list[dict[str, Any]]] = {}
    for depth in range(1, max_depth + 1):
        additions: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for type_def in metadata.types:
            for field in metadata.fields_for(type_def):
                field_type = runtime.type_name(field.type_index)
                if field_type not in target_names:
                    continue
                field_rows = runtime.layout(type_def.index)
                field_row = next(
                    (row for row in field_rows if row["token"] == f"0x{field.token:08x}"),
                    None,
                )
                if field_row is None or int(field_row["offset"]) >= 0x80000000:
                    continue
                tails = (
                    [{"types": [carrier_type], "fields": [], "offsets": []}]
                    if field_type == carrier_type
                    else paths_by_type.get(type_index_by_name.get(field_type, -1), [])
                )
                for tail in tails:
                    row = {
                        "types": [metadata.type_full_name(type_def), *tail["types"]],
                        "fields": [field_row["name"], *tail["fields"]],
                        "offsets": [int(field_row["offset"]), *tail["offsets"]],
                    }
                    if row not in additions[type_def.index]:
                        additions[type_def.index].append(row)
        if not additions:
            break
        for type_index, rows in additions.items():
            bucket = paths_by_type.setdefault(type_index, [])
            for row in rows:
                if row not in bucket:
                    bucket.append(row)
        target_names.update(
            metadata.type_full_name(metadata.types[type_index]) for type_index in additions
        )
    # A derived class uses its base instance-field offsets unchanged.  IL2CPP
    # metadata lists only fields declared on the derived type, so propagate
    # carrier paths through the installed inheritance graph explicitly.
    children_by_parent: dict[str, list[int]] = defaultdict(list)
    for type_def in metadata.types:
        type_name = metadata.type_full_name(type_def)
        parent_name = runtime.type_name(type_def.parent_index)
        # This installed v29 dialect retains an extra type slot.  The shared
        # parser exposes the nominal parent slot as the type's own by-value
        # row, while the preceding slot resolves the actual base class.  Make
        # that layout distinction from resolved identities rather than from a
        # particular class name.
        if parent_name == type_name:
            alternate_parent = runtime.type_name(type_def.declaring_type_index)
            if alternate_parent != type_name:
                parent_name = alternate_parent
        if parent_name in type_index_by_name:
            children_by_parent[parent_name].append(type_def.index)
    queue = list(paths_by_type)
    propagated: set[tuple[int, int]] = set()
    while queue:
        parent_index = queue.pop(0)
        parent_name = metadata.type_full_name(metadata.types[parent_index])
        for child_index in children_by_parent.get(parent_name, []):
            edge = (parent_index, child_index)
            if edge in propagated:
                continue
            propagated.add(edge)
            child_name = metadata.type_full_name(metadata.types[child_index])
            bucket = paths_by_type.setdefault(child_index, [])
            added = False
            for parent_path in paths_by_type[parent_index]:
                if child_name in parent_path["types"]:
                    continue
                inherited = {
                    "types": [child_name, *parent_path["types"]],
                    "fields": list(parent_path["fields"]),
                    "offsets": list(parent_path["offsets"]),
                }
                if inherited not in bucket:
                    bucket.append(inherited)
                    added = True
            if added:
                queue.append(child_index)
    return paths_by_type


def memory_base(expr: str) -> tuple[str, int] | None:
    clean = expr.split("=>", 1)[0].replace(" ", "")
    match = re.fullmatch(r"([a-z][a-z0-9]*)([+-]0x[0-9a-f]+)?", clean)
    if not match:
        return None
    displacement = int(match.group(2), 0) if match.group(2) else 0
    return match.group(1), displacement


def resolve_argument_value(
    mapper: Any,
    instructions: list[dict[str, Any]],
    call_index: int,
    target_row: dict[str, Any],
    parameter_index: int,
) -> dict[str, Any]:
    instance_slot = 0 if mapper.is_static_method(target_row) else 1
    slot = instance_slot + parameter_index
    start = max(
        [index + 1 for index in range(call_index) if str(instructions[index].get("text") or "").startswith("call ")]
        or [0]
    )

    def last_register_value(register: str, before: int) -> tuple[str, int] | None:
        canonical = mapper.canonical_register(register)
        for index in range(before - 1, start - 1, -1):
            write = instructions[index].get("write") or {}
            if mapper.canonical_register(str(write.get("register") or "")) == canonical:
                return str(write.get("value") or ""), index
        return None

    source = ""
    source_index = call_index
    location = ""
    if slot < 4:
        register = ("rcx", "rdx", "r8", "r9")[slot]
        location = register
        found = last_register_value(register, call_index)
        if found:
            source, source_index = found
    else:
        stack_offset = 0x20 + (slot - 4) * 8
        location = f"[rsp+0x{stack_offset:x}]"
        pattern = re.compile(rf"^(?:mov|lea) \[rsp\+0x{stack_offset:x}\], (.+)$")
        for index in range(call_index - 1, start - 1, -1):
            match = pattern.match(str(instructions[index].get("text") or ""))
            if match:
                source = match.group(1)
                source_index = index
                break
    canonical_source = mapper.canonical_register(source)
    if canonical_source:
        found = last_register_value(canonical_source, source_index)
        if found:
            prior, prior_index = found
            if prior.startswith("&[") or source.startswith("["):
                source, source_index = prior, prior_index
    local_expr = source[2:-1] if source.startswith("&[") and source.endswith("]") else ""
    return {
        "abiSlot": slot,
        "abiLocation": location,
        "source": source,
        "sourceInstructionOffset": int(instructions[source_index].get("offset") or 0),
        "localExpression": local_expr,
        "classification": "stack_local" if local_expr else "forwarded_or_unresolved",
    }


def local_initializer(
    mapper: Any,
    instructions: list[dict[str, Any]],
    call_index: int,
    argument: dict[str, Any],
    carrier_size: int,
    focus_fields: list[dict[str, Any]],
) -> dict[str, Any]:
    expression = str(argument.get("localExpression") or "")
    parsed = memory_base(expression)
    if parsed is None:
        return {
            "classification": argument.get("classification"),
            "writes": [],
            "focusFieldStates": {
                field["name"]: "forwarded_or_unresolved" for field in focus_fields
            },
        }
    base_register, base_offset = parsed
    zeros = instruction_zero_sources(mapper, instructions[:call_index])
    states: list[str] = ["unwritten"] * carrier_size
    writes: list[dict[str, Any]] = []
    pattern = re.compile(r"^(?:mov(?:aps|ups|dqu|sd)?|and) \[([^\]]+)\], (.+)$")
    for instruction in instructions[:call_index]:
        match = pattern.match(str(instruction.get("text") or ""))
        if not match:
            continue
        destination = memory_base(match.group(1))
        if destination is None or destination[0] != base_register:
            continue
        relative = destination[1] - base_offset
        width = field_width(instruction)
        if relative >= carrier_size or relative + width <= 0:
            continue
        is_zero = zeros.get(int(instruction.get("offset") or 0), False)
        state = "zero" if is_zero else "unknown"
        for byte_index in range(max(0, relative), min(carrier_size, relative + width)):
            states[byte_index] = state
        writes.append({
            "va": instruction.get("va"),
            "offset": relative,
            "width": width,
            "state": state,
            "instruction": instruction.get("text"),
        })
    focus_states: dict[str, str] = {}
    for field in focus_fields:
        selected = states[field["offset"]:field["offset"] + field["width"]]
        focus_states[field["name"]] = (
            "zero" if selected and all(value == "zero" for value in selected)
            else "unwritten" if selected and all(value == "unwritten" for value in selected)
            else "unknown"
        )
    return {
        "classification": "stack_local_initialized",
        "localExpression": expression,
        "writes": writes,
        "focusFieldStates": focus_states,
    }


def scan_direct_calls(
    pe: Any,
    pointers: list[int],
    methods_by_pointer: dict[int, list[dict[str, Any]]],
    targets: set[int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section in pe.sections:
        if section["name"] not in {".text", "il2cpp"}:
            continue
        data = pe.buf[section["rawPointer"]:section["rawPointer"] + section["rawSize"]]
        position = data.find(b"\xe8")
        while position >= 0:
            if position + 5 <= len(data):
                call_va = pe.image_base + section["virtualAddress"] + position
                target_va = call_va + 5 + struct.unpack_from("<i", data, position + 1)[0]
                if target_va in targets:
                    caller_index = bisect.bisect_right(pointers, call_va) - 1
                    if caller_index >= 0:
                        caller_va = pointers[caller_index]
                        next_va = (
                            pointers[caller_index + 1]
                            if caller_index + 1 < len(pointers)
                            else caller_va + MAX_METHOD_BYTES
                        )
                        if call_va < min(next_va, caller_va + MAX_METHOD_BYTES):
                            rows.append({
                                "callVa": f"0x{call_va:x}",
                                "callerVa": f"0x{caller_va:x}",
                                "targetVa": f"0x{target_va:x}",
                                "callers": methods_by_pointer.get(caller_va) or [],
                                "targets": methods_by_pointer.get(target_va) or [],
                            })
            position = data.find(b"\xe8", position + 1)
    return rows


def build_report(
    gameassembly: Path,
    metadata_path: Path,
    carrier_type: str,
    focus_field_names: Iterable[str],
    *,
    max_container_depth: int = MAX_CONTAINER_DEPTH,
) -> dict[str, Any]:
    if not gameassembly.is_file() or not metadata_path.is_file():
        raise AuditError(f"missing original binary input: {gameassembly} / {metadata_path}")
    mapper = load_module("native_value_carrier_mapper", MAPPER_PATH)
    catalog = load_module("native_value_carrier_catalog", CATALOG_PATH)
    metadata = catalog.Metadata(metadata_path)
    pe = mapper.PeImage(gameassembly)
    registration = mapper.find_metadata_registration(pe, mapper.DEFAULT_CODE_REGISTRATION)
    if registration is None:
        raise AuditError("could not derive MetadataRegistration from current GameAssembly")
    runtime = RuntimeTypes(pe, metadata, mapper, registration)

    carrier_types = [
        type_def for type_def in metadata.types
        if metadata.type_full_name(type_def) == carrier_type
    ]
    if len(carrier_types) != 1:
        raise AuditError(
            f"carrier type must resolve exactly once: {carrier_type!r} -> {len(carrier_types)}"
        )
    carrier = carrier_types[0]
    size = runtime.size(carrier.index)
    native_size = int(size["nativeSize"])
    layout = runtime.layout(carrier.index)
    focus_names = list(dict.fromkeys(focus_field_names)) or [row["name"] for row in layout]
    missing_focus = sorted(set(focus_names) - {row["name"] for row in layout})
    if missing_focus:
        raise AuditError(f"focus fields absent from {carrier_type}: {missing_focus}")
    sorted_layout = sorted(layout, key=lambda row: int(row["offset"]))
    focus_fields: list[dict[str, Any]] = []
    for index, field in enumerate(sorted_layout):
        if field["name"] not in focus_names:
            continue
        next_offset = (
            int(sorted_layout[index + 1]["offset"])
            if index + 1 < len(sorted_layout)
            else native_size
        )
        focus_fields.append({
            **field,
            "width": scalar_field_width(
                str(field["type"]), native_size, int(field["offset"]), next_offset
            ),
        })

    pointers, methods_by_pointer, pointers_by_method = build_pointer_index(pe, metadata, mapper)
    container_map = container_paths(
        metadata, runtime, carrier_type, max_depth=max_container_depth
    )
    owner_name_by_index = {
        type_def.index: metadata.type_full_name(type_def) for type_def in metadata.types
    }

    signature_rows: dict[int, dict[str, Any]] = {}
    for type_def in metadata.types:
        owner = owner_name_by_index[type_def.index]
        for method in metadata.methods_for(type_def):
            row = mapped_method_row(metadata, catalog, runtime, method.index, owner)
            parameters = [
                parameter for parameter in row.get("parameterDetails") or []
                if parameter.get("typeName") == carrier_type
            ]
            if parameters or row.get("returnTypeName") == carrier_type:
                row["carrierParameters"] = [parameter["name"] for parameter in parameters]
                row["returnsCarrier"] = row.get("returnTypeName") == carrier_type
                signature_rows[method.index] = row

    method_indexes = set(signature_rows)
    for type_index in container_map:
        method_indexes.update(
            method.index for method in metadata.methods_for(metadata.types[type_index])
        )

    access_rows: list[dict[str, Any]] = []
    decoded_methods: list[dict[str, Any]] = []
    for method_index in sorted(method_indexes):
        owner_index = metadata.methods[method_index].declaring_type
        owner = owner_name_by_index[owner_index]
        row = signature_rows.get(method_index) or mapped_method_row(
            metadata, catalog, runtime, method_index, owner
        )
        method_pointers = sorted(pointers_by_method.get(method_index) or [])
        if not method_pointers:
            continue
        roots: list[tuple[str, list[int], str]] = []
        for parameter in row.get("parameterDetails") or []:
            if parameter.get("typeName") == carrier_type:
                roots.append((f"param:{parameter['name']}", [], "signature_parameter"))
        if owner == carrier_type:
            roots.append(("this", [], "carrier_instance"))
        for path in container_map.get(owner_index) or []:
            offsets = list(path["offsets"])
            roots.append(("this", offsets, "nested_container"))

        for pointer in method_pointers:
            body = method_body(pe, pointers, pointer)
            summary = mapper.build_method_body_summary(
                row,
                body,
                pointer,
                methods_by_pointer,
                pe=pe,
                max_instructions=2000,
            )
            instructions = mapper.decode_x64_subset(body, pointer, stop_offset=len(body))
            zero_sources = instruction_zero_sources(mapper, instructions)
            method_access_count = 0
            for access in summary.get("fieldAccesses") or []:
                if str(access.get("text") or "").startswith("lea "):
                    continue
                instruction_offset = int(access.get("offset") or 0)
                width = field_width(next(
                    (
                        instruction for instruction in instructions
                        if int(instruction.get("offset") or 0) == instruction_offset
                    ),
                    {"text": access.get("text"), "bytes": access.get("bytes")},
                ))
                for root, container_offsets, path_kind in roots:
                    for field in focus_fields:
                        expected_path = (
                            [*container_offsets[:-1], container_offsets[-1] + field["offset"]]
                            if container_offsets
                            else [field["offset"]]
                        )
                        if not access_overlaps_path(
                            str(access.get("origin") or ""),
                            root,
                            expected_path,
                            width,
                            int(field["width"]),
                        ):
                            continue
                        method_access_count += 1
                        access_rows.append({
                            "field": field["name"],
                            "kind": access.get("kind"),
                            "writeState": (
                                "zero" if access.get("kind") == "write"
                                and zero_sources.get(instruction_offset, False)
                                else "unknown" if access.get("kind") == "write"
                                else None
                            ),
                            "pathKind": path_kind,
                            "root": root,
                            "expectedPath": [f"0x{value:x}" for value in expected_path],
                            "origin": access.get("origin"),
                            "method": f"{owner}.{row['method']}",
                            "token": row["token"],
                            "methodVa": f"0x{pointer:x}",
                            "instructionVa": access.get("va"),
                            "instruction": access.get("text"),
                            "width": width,
                        })
            decoded_methods.append({
                "method": f"{owner}.{row['method']}",
                "token": row["token"],
                "methodVa": f"0x{pointer:x}",
                "carrierParameters": row.get("carrierParameters") or [],
                "returnsCarrier": bool(row.get("returnsCarrier")),
                "focusAccessCount": method_access_count,
                "instructionCount": summary.get("instructionCount"),
                "unknownInstructionCount": summary.get("unknownInstructionCount"),
            })

    signature_targets = {
        pointer
        for method_index in signature_rows
        for pointer in pointers_by_method.get(method_index) or []
    }
    direct_calls = scan_direct_calls(pe, pointers, methods_by_pointer, signature_targets)
    target_rows_by_pointer: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for method_index, row in signature_rows.items():
        for pointer in pointers_by_method.get(method_index) or []:
            target_rows_by_pointer[pointer].append(row)

    initializer_rows: list[dict[str, Any]] = []
    caller_instruction_cache: dict[int, list[dict[str, Any]]] = {}
    for call in direct_calls:
        target_va = parse_hex(call["targetVa"])
        caller_va = parse_hex(call["callerVa"])
        instructions = caller_instruction_cache.get(caller_va)
        if instructions is None:
            body = method_body(pe, pointers, caller_va)
            instructions = mapper.decode_x64_subset(body, caller_va, stop_offset=len(body))
            caller_instruction_cache[caller_va] = instructions
        call_va = parse_hex(call["callVa"])
        call_index = next(
            (
                index for index, instruction in enumerate(instructions)
                if parse_hex(instruction.get("va")) == call_va
            ),
            -1,
        )
        if call_index < 0:
            continue
        for target_row in target_rows_by_pointer.get(target_va) or []:
            for parameter_index, parameter in enumerate(target_row.get("parameterDetails") or []):
                if parameter.get("typeName") != carrier_type:
                    continue
                argument = resolve_argument_value(
                    mapper, instructions, call_index, target_row, parameter_index
                )
                initializer = local_initializer(
                    mapper,
                    instructions,
                    call_index,
                    argument,
                    native_size,
                    focus_fields,
                )
                initializer_rows.append({
                    "callerVa": call["callerVa"],
                    "callVa": call["callVa"],
                    "targetVa": call["targetVa"],
                    "callers": call["callers"],
                    "target": f"{target_row['type']}.{target_row['method']}",
                    "targetToken": target_row["token"],
                    "parameter": parameter["name"],
                    "argument": argument,
                    "initializer": initializer,
                })

    focus_summary: dict[str, dict[str, Any]] = {}
    for field in focus_fields:
        field_accesses = [row for row in access_rows if row["field"] == field["name"]]
        initializer_states = Counter(
            row["initializer"]["focusFieldStates"].get(field["name"], "missing")
            for row in initializer_rows
        )
        focus_summary[field["name"]] = {
            "offset": f"0x{field['offset']:x}",
            "width": field["width"],
            "readAccesses": sum(row["kind"] == "read" for row in field_accesses),
            "writeAccesses": sum(row["kind"] == "write" for row in field_accesses),
            "zeroWriteAccesses": sum(row.get("writeState") == "zero" for row in field_accesses),
            "unknownWriteAccesses": sum(row.get("writeState") == "unknown" for row in field_accesses),
            "directCallInitializerStates": dict(sorted(initializer_states.items())),
        }

    failures: list[dict[str, Any]] = []
    unknown_decodes = [row for row in decoded_methods if row["unknownInstructionCount"]]
    if not signature_rows or not signature_targets:
        failures.append({
            "validator": "nativeValueCarrierAudit",
            "gate": "mappedCarrierSignatureSurface",
            "sourceFile": str(metadata_path.resolve()),
            "expected": {"signatureMethodsGreaterThan": 0, "mappedPointersGreaterThan": 0},
            "actual": {
                "signatureMethods": len(signature_rows),
                "mappedPointers": len(signature_targets),
            },
            "sourceHashes": {"globalMetadataSha256": sha256_file(metadata_path)},
        })

    game_hash = sha256_file(gameassembly)
    metadata_hash = sha256_file(metadata_path)
    return {
        "schema": "nativeValueCarrierAudit.v1",
        "configuration": {
            "carrierType": carrier_type,
            "focusFields": focus_names,
            "maxContainerDepth": max_container_depth,
            "contentIdentityInputs": [],
            "ocrInputs": [],
            "manualOverrideInputs": [],
        },
        "source": {
            "gameAssembly": str(gameassembly.resolve()),
            "gameAssemblySha256": game_hash,
            "globalMetadata": str(metadata_path.resolve()),
            "globalMetadataSha256": metadata_hash,
            "codeRegistrationVa": f"0x{mapper.DEFAULT_CODE_REGISTRATION:x}",
            "metadataRegistrationVa": f"0x{registration:x}",
        },
        "carrier": {
            "type": carrier_type,
            "typeDefinitionIndex": carrier.index,
            "typeToken": f"0x{carrier.token:08x}",
            "instanceSize": size["instanceSize"],
            "nativeSize": native_size,
            "fields": [
                {**row, "offset": f"0x{int(row['offset']):x}"} for row in layout
            ],
        },
        "containerPaths": [
            {
                "rootType": owner_name_by_index[type_index],
                **{
                    **path,
                    "offsets": [f"0x{value:x}" for value in path["offsets"]],
                },
            }
            for type_index in sorted(container_map)
            for path in container_map[type_index]
        ],
        "signatureMethods": [
            {
                "type": row["type"],
                "method": row["method"],
                "token": row["token"],
                "parameters": [
                    {"name": parameter["name"], "type": parameter["typeName"]}
                    for parameter in row.get("parameterDetails") or []
                ],
                "returnType": row["returnTypeName"],
                "carrierParameters": row["carrierParameters"],
                "returnsCarrier": row["returnsCarrier"],
                "methodPointers": [
                    f"0x{pointer:x}" for pointer in sorted(pointers_by_method.get(index) or [])
                ],
            }
            for index, row in sorted(signature_rows.items())
        ],
        "decodedMethods": decoded_methods,
        "fieldAccesses": access_rows,
        "directCallsites": direct_calls,
        "directCallInitializers": initializer_rows,
        "focusFieldSummary": focus_summary,
        "summary": {
            "carrierFields": len(layout),
            "focusFields": len(focus_fields),
            "containerPaths": sum(len(rows) for rows in container_map.values()),
            "signatureMethods": len(signature_rows),
            "mappedSignaturePointers": len(signature_targets),
            "decodedMethods": len(decoded_methods),
            "focusFieldAccesses": len(access_rows),
            "directCallsites": len(direct_calls),
            "directCarrierArguments": len(initializer_rows),
            "methodsWithUnknownDecodedInstructions": len(unknown_decodes),
        },
        "decodeDiagnostics": {
            "methodsWithUnknownInstructions": len(unknown_decodes),
            "firstMethods": unknown_decodes[:10],
            "interpretation": (
                "The shared lightweight decoder preserves undecoded opcodes as "
                "diagnostics. Contract-specific validators must lock the exact "
                "field accesses they consume; an undecoded opcode is never promoted "
                "to a producer or consumer edge."
            ),
        },
        "validation": {
            "status": "validation_failed" if failures else "validated",
            "failures": failures,
        },
        "evidenceBoundary": (
            "The installed metadata defines the carrier layout and the installed "
            "GameAssembly defines every reported native pointer, direct callsite, "
            "field access, and local initializer. This bounded static audit does not "
            "claim coverage of virtual/interface dispatch, reflection, XLua, live "
            "server values, execution in a particular session, mission ownership, "
            "branch choice, or chronology."
        ),
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    carrier = report["carrier"]
    lines = [
        f"# Native Value Carrier Audit: {md_escape(carrier['type'])}",
        "",
        f"- Native size: **0x{carrier['nativeSize']:x}**",
        f"- Signature methods / mapped pointers: **{summary['signatureMethods']} / {summary['mappedSignaturePointers']}**",
        f"- Nested container paths: **{summary['containerPaths']}**",
        f"- Direct callsites / carrier arguments: **{summary['directCallsites']} / {summary['directCarrierArguments']}**",
        f"- Validation: **{report['validation']['status']}**",
        f"- GameAssembly SHA-256: `{report['source']['gameAssemblySha256']}`",
        f"- Metadata SHA-256: `{report['source']['globalMetadataSha256']}`",
        "",
        "## Focus fields",
        "",
        "| Field | Offset | Reads | Writes | Zero writes | Direct initializer states |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name, row in report["focusFieldSummary"].items():
        states = ", ".join(
            f"{key}={value}" for key, value in row["directCallInitializerStates"].items()
        ) or "none"
        lines.append(
            f"| `{md_escape(name)}` | `{row['offset']}` | {row['readAccesses']} | "
            f"{row['writeAccesses']} | {row['zeroWriteAccesses']} | {md_escape(states)} |"
        )
    lines.extend([
        "",
        "## Boundary",
        "",
        report["evidenceBoundary"],
        "",
    ])
    return "\n".join(lines)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--carrier-type", required=True)
    parser.add_argument("--focus-field", action="append", default=[])
    parser.add_argument("--max-container-depth", type=int, default=MAX_CONTAINER_DEPTH)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)


def run(args: argparse.Namespace) -> int:
    try:
        report = build_report(
            args.gameassembly,
            args.metadata,
            args.carrier_type,
            args.focus_field,
            max_container_depth=args.max_container_depth,
        )
    except (AuditError, OSError, ValueError, struct.error) as exc:
        print(f"native value carrier audit failed: {exc}", file=sys.stderr)
        return 1
    write_report_json(args.json, report)
    write_text_if_changed(args.markdown, markdown_report(report))
    if args.carrier_type == "Beyond.Gameplay.TeleportParam":
        if __package__ == "scripts.story_recovery.native_carriers":
            from ...story_builder.native_contracts.teleport_param import (
                DEFAULT_CONTRACT,
                reconcile_generic_audit,
            )
        elif __package__ == "story_recovery.native_carriers":
            from story_builder.native_contracts.teleport_param import (
                DEFAULT_CONTRACT,
                reconcile_generic_audit,
            )
        else:  # pragma: no cover - checked at import time
            raise ImportError(f"unsupported package identity: {__package__!r}")
        try:
            contract = json.loads(DEFAULT_CONTRACT.read_text(encoding="utf-8-sig"))
            reconciliation_failures = reconcile_generic_audit(report, contract)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            reconciliation_failures = [{
                "validator": "teleportParamNativeContractReconciliation",
                "gate": "read_contract",
                "sourceFile": str(DEFAULT_CONTRACT),
                "expected": {"readableJsonObject": True},
                "actual": str(exc)[:400],
            }]
        if reconciliation_failures:
            failure = reconciliation_failures[0]
            print(
                "TeleportParam contract reconciliation failed: "
                f"validator={failure['validator']}; gate={failure['gate']}; "
                f"source={failure['sourceFile']}; "
                f"expected={failure['expected']!r}; actual={failure['actual']!r}",
                file=sys.stderr,
            )
            return 1
        print("TeleportParam production contract reconciliation: validated")
    summary = report["summary"]
    print(
        "Native value carrier audit "
        f"{report['validation']['status']}: {report['carrier']['type']}, "
        f"{summary['signatureMethods']} signature methods, "
        f"{summary['directCallsites']} direct callsites, "
        f"{summary['focusFieldAccesses']} focus-field accesses"
    )
    if report["validation"]["status"] != "validated":
        failure = report["validation"]["failures"][0]
        print(
            "first failure: "
            f"validator={failure.get('validator')}; gate={failure.get('gate')}; "
            f"source={failure.get('sourceFile')}; expected={failure.get('expected')!r}; "
            f"actual={failure.get('actual')!r}",
            file=sys.stderr,
        )
        return 1
    return 0
