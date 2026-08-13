"""Report-neutral IL2CPP metadata and runtime-table helpers.

This module owns byte decoding, metadata constants, runtime type names, and
field offsets. It deliberately has no dependency on ``protocol_registry`` or
on any report schema.
"""
from __future__ import annotations

import importlib.util
import re
import struct
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=None)
def load_metadata_helper(path: Path) -> Any:
    """Load the metadata helper once, preserving its exception identities."""
    spec = importlib.util.spec_from_file_location("endfield_protocol_metadata", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load metadata helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_native_mapper(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("endfield_protocol_native_mapper", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load native mapper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNTIME_PRIMITIVE_TYPE_NAMES = {
    0x01: "void",
    0x02: "bool",
    0x03: "char",
    0x04: "sbyte",
    0x05: "byte",
    0x06: "short",
    0x07: "ushort",
    0x08: "int",
    0x09: "uint",
    0x0A: "long",
    0x0B: "ulong",
    0x0C: "float",
    0x0D: "double",
    0x0E: "string",
    0x18: "nint",
    0x19: "nuint",
    0x1C: "object",
}


def runtime_generic_inst_type_pointers(pe: Any, generic_inst_va: int) -> list[int]:
    offset, _section, _rva = pe.file_offset_for_va(generic_inst_va)
    if offset is None:
        raise RuntimeError(
            f"generic instantiation VA is outside GameAssembly: 0x{generic_inst_va:x}"
        )
    argc, argv_va = struct.unpack_from("<QQ", pe.buf, offset)
    if argc > 64:
        raise RuntimeError(
            f"implausible generic argument count {argc} at 0x{generic_inst_va:x}"
        )
    return [pe.u64_at_va(argv_va + index * 8) for index in range(argc)]


def runtime_type_name(
    pe: Any,
    metadata: Any,
    type_va: int,
    *,
    depth: int = 0,
    seen: frozenset[int] = frozenset(),
) -> str:
    """Name one MetadataRegistration Il2CppType, including generic instances."""
    if depth > 12:
        return "<generic-depth-limit>"
    if type_va in seen:
        return f"<recursive-type:0x{type_va:x}>"
    offset, _section, _rva = pe.file_offset_for_va(type_va)
    if offset is None:
        return f"<type-va-outside-image:0x{type_va:x}>"
    data = struct.unpack_from("<Q", pe.buf, offset)[0]
    type_code = pe.buf[offset + 10]
    primitive = RUNTIME_PRIMITIVE_TYPE_NAMES.get(type_code)
    if primitive is not None:
        return primitive
    if type_code in {0x11, 0x12}:
        if 0 <= data < len(metadata.types):
            return metadata.type_full_name(metadata.types[data])
        return f"<type-definition:{data}>"
    if type_code == 0x15:
        generic_offset, _section, _rva = pe.file_offset_for_va(data)
        if generic_offset is None:
            return f"<generic-class-va-outside-image:0x{data:x}>"
        definition_type_va, class_inst_va = struct.unpack_from(
            "<QQ", pe.buf, generic_offset
        )
        next_seen = seen | {type_va}
        definition_name = runtime_type_name(
            pe, metadata, definition_type_va, depth=depth + 1, seen=next_seen
        )
        arguments = [
            runtime_type_name(
                pe,
                metadata,
                argument_type_va,
                depth=depth + 1,
                seen=next_seen,
            )
            for argument_type_va in runtime_generic_inst_type_pointers(
                pe, class_inst_va
            )
        ]
        return f"{definition_name}<{','.join(arguments)}>"
    if type_code in {0x13, 0x1E}:  # IL2CPP_TYPE_VAR / MVAR
        kind = "VAR" if type_code == 0x13 else "MVAR"
        return f"{kind}[{data}]"
    if type_code == 0x0F:
        return runtime_type_name(
            pe, metadata, data, depth=depth + 1, seen=seen | {type_va}
        ) + "*"
    if type_code == 0x1D:
        return runtime_type_name(
            pe, metadata, data, depth=depth + 1, seen=seen | {type_va}
        ) + "[]"
    return f"<runtime-type:0x{type_code:x}:data=0x{data:x}>"


def read_compressed_uint32(data: bytes, offset: int) -> tuple[int, int]:
    first = data[offset]
    if first & 0x80 == 0:
        return first, 1
    if first & 0xC0 == 0x80:
        return ((first & 0x3F) << 8) | data[offset + 1], 2
    if first & 0xE0 == 0xC0:
        return (
            ((first & 0x1F) << 24)
            | (data[offset + 1] << 16)
            | (data[offset + 2] << 8)
            | data[offset + 3],
            4,
        )
    if first == 0xF0:
        return struct.unpack_from(">I", data, offset + 1)[0], 5
    if first == 0xFE:
        return 0xFFFFFFFE, 1
    if first == 0xFF:
        return 0xFFFFFFFF, 1
    raise ValueError(f"unsupported compressed uint prefix 0x{first:02x}")


def read_compressed_int32(data: bytes, offset: int) -> tuple[int, int]:
    unsigned, size = read_compressed_uint32(data, offset)
    return (unsigned >> 1) ^ -(unsigned & 1), size


def normalized_field_name(value: str) -> str:
    if value.endswith("FieldNumber"):
        value = value[: -len("FieldNumber")]
    value = value.rstrip("_")
    return re.sub(r"[^a-z0-9]", "", value.lower())


def field_defaults(metadata: Any) -> dict[int, tuple[int, int]]:
    section = metadata.sections["fieldDefaultValues"]
    if section.size % 12:
        raise RuntimeError("fieldDefaultValues is not aligned to 12-byte records")
    out: dict[int, tuple[int, int]] = {}
    for position in range(section.offset, section.offset + section.size, 12):
        field_index, type_index, data_index = struct.unpack_from(
            "<iii", metadata.buf, position
        )
        if field_index in out:
            raise RuntimeError(f"duplicate field default for field {field_index}")
        out[field_index] = (type_index, data_index)
    return out


def constant_value(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    field: Any,
) -> int | None:
    default = defaults.get(field.index)
    if default is None:
        return None
    _type_index, data_index = default
    section = metadata.sections["fieldAndParameterDefaultValueData"]
    value, _size = read_compressed_int32(metadata.buf, section.offset + data_index)
    return value


def enum_members(
    metadata: Any,
    defaults: dict[int, tuple[int, int]],
    type_name: str,
) -> list[dict[str, Any]]:
    for type_def in metadata.types:
        if metadata.type_full_name(type_def) != type_name:
            continue
        rows: list[dict[str, Any]] = []
        for field in metadata.fields_for(type_def):
            name = metadata.string(field.name_index)
            if name == "value__":
                continue
            value = constant_value(metadata, defaults, field)
            if value is None:
                continue
            rows.append({
                "id": value,
                "name": name,
                "fieldIndex": field.index,
                "token": f"0x{field.token:08x}",
            })
        return sorted(rows, key=lambda row: (row["id"], row["name"]))
    raise RuntimeError(f"metadata type not found: {type_name}")


def runtime_type_field_offsets(
    metadata: Any,
    pe: Any,
    metadata_registration_summary: dict[str, Any],
    type_index: int,
) -> dict[str, int]:
    """Read one type's current-build instance offsets from MetadataRegistration."""
    table_count = int(metadata_registration_summary["fieldOffsetsCount"])
    if not 0 <= type_index < table_count:
        raise RuntimeError(
            f"field-offset type index {type_index} outside current table count {table_count}"
        )
    table_va = int(metadata_registration_summary["fieldOffsets"], 16)
    type_offsets_va = pe.u64_at_va(table_va + type_index * 8)
    if not type_offsets_va:
        raise RuntimeError(f"type {type_index} has no runtime field-offset row")
    type_def = metadata.types[type_index]
    return {
        metadata.string(field.name_index): pe.u32_at_va(type_offsets_va + index * 4)
        for index, field in enumerate(metadata.fields_for(type_def))
    }
