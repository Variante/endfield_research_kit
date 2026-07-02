#!/usr/bin/env python3
"""
Catalog IL2CPP metadata tables for Endfield dialog option-flow recovery.

Instead of scanning for identifier strings only, it parses
`global-metadata.dat` type, field, method, parameter, image, and nested-type
tables. The output is intended to answer recovery questions such as:

- which runtime classes own option/timeline/trunk fields?
- which option-related methods are worth recovering from GameAssembly bodies?
- did a game update add/remove fields or method names in the option flow?

The script is offline-only. It does not need the game process or
MetadataRegistration.

Usage:
  python tools/endfield-il2cpp/catalog_option_flow_metadata.py
  python tools/endfield-il2cpp/catalog_option_flow_metadata.py --cache-metadata
  python tools/endfield-il2cpp/catalog_option_flow_metadata.py --only-focus
  python tools/endfield-il2cpp/catalog_option_flow_metadata.py --only-focus --body-context 4
  python tools/endfield-il2cpp/catalog_option_flow_metadata.py --out reports/option_flow_runtime_metadata.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_INSTALL_METADATA = Path(
    r"D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat"
)
DEFAULT_CACHE_METADATA = Path("export_full/recovered/il2cpp/global-metadata.dat")

DEFAULT_JSON = Path("reports/option_flow_runtime_metadata.json")
DEFAULT_MD = Path("reports/option_flow_runtime_metadata.md")
DEFAULT_BODY_CONTEXT = 3

DEFAULT_TYPE_RE = re.compile(
    r"(?:"
    r"Dialog.*(?:Option|Timeline|Tree|Trunk|Manager|Behaviour|Controller)|"
    r"(?:Timeline|Playable|Track|RuntimeJump).*(?:Dialog|Option|Trunk)|"
    r"Option.*(?:Dialog|Timeline|Playable|Branch|Behaviour|Condition)|"
    r"DialogOption|DialogTimelineOption|DialogTreeOption|DialogTrunk"
    r")",
    re.IGNORECASE,
)

DEFAULT_MEMBER_RE = re.compile(
    r"(?:"
    r"option|choice|select|selected|choose|branch|target|jump|trunk|"
    r"dialog|timeline|playable|track|director|condition|logic|finish|"
    r"panel|route|next|skip"
    r")",
    re.IGNORECASE,
)

DEFAULT_IMAGE_RE = re.compile(r"Beyond", re.IGNORECASE)

BODY_TARGET_METHOD_RE = re.compile(
    r"^(?:"
    r"GenPlayable|InitDialogOptions|InitDialogTrunk|ProcessFrame|"
    r"TryTriggerTrunkBindingOption|SetDialogOption|ResetDialogOption|"
    r"_SelectIndexInTimeline|SelectIndex|OnJumpForward|_TryDoNext|"
    r"DialogChooseOption|DialogTimelineDoNext|DialogTimelineGetAllTimelinePlayable|"
    r"DialogTimelineGetAllActiveClips|DialogTimelineDisableLoopInRange|"
    r"GetNextIndex|GetChatOptionData|_TryShowOptions|DoExecute|"
    r"StartDialog|Next|SkipToNextShowNode"
    r")$"
)

FOCUS_TYPE_NAMES = {
    "DialogManager",
    "DialogUtils",
    "DialogOptionBehaviour",
    "DialogOptionData",
    "DialogOptionInfo",
    "DialogOptionPlayableAsset",
    "DialogSignOptionPlayableAsset",
    "DialogOptionTable",
    "DialogTimelineOptionData",
    "DialogTimelineOptionPlayableAsset",
    "DialogTimelineOptionTrack",
    "DialogTimelineManager",
    "DialogTrunkBehaviour",
    "DialogTreeController",
    "DialogTreeOptionNode",
    "DialogTreeOptionInfo",
    "DialogTreeExOptionNode",
}


@dataclass(frozen=True)
class Section:
    name: str
    offset: int
    size: int

    def count(self, record_size: int) -> int:
        if record_size <= 0:
            return 0
        return self.size // record_size


@dataclass
class TypeDef:
    index: int
    name_index: int
    namespace_index: int
    byval_type_index: int
    byref_type_index: int | None
    declaring_type_index: int
    parent_index: int
    element_type_index: int | None
    generic_container_index: int
    flags: int
    field_start: int
    method_start: int
    event_start: int
    property_start: int
    nested_types_start: int
    interfaces_start: int
    vtable_start: int
    interface_offsets_start: int
    method_count: int
    property_count: int
    field_count: int
    event_count: int
    nested_type_count: int
    vtable_count: int
    interfaces_count: int
    interface_offsets_count: int
    bitfield: int
    token: int


@dataclass
class MethodDef:
    index: int
    name_index: int
    declaring_type: int
    return_type: int
    return_parameter_token: int | None
    parameter_start: int
    generic_container_index: int
    token: int
    flags: int
    iflags: int
    slot: int
    parameter_count: int


@dataclass
class FieldDef:
    index: int
    name_index: int
    type_index: int
    token: int


@dataclass
class ParameterDef:
    index: int
    name_index: int
    token: int
    type_index: int


@dataclass
class ImageDef:
    index: int
    name_index: int
    assembly_index: int
    type_start: int
    type_count: int
    exported_type_start: int
    exported_type_count: int
    entry_point_index: int
    token: int
    custom_attribute_start: int
    custom_attribute_count: int


class MetadataParseError(RuntimeError):
    pass


class Metadata:
    def __init__(self, path: Path):
        self.path = path
        self.buf = path.read_bytes()
        self.magic, self.version = struct.unpack_from("<II", self.buf, 0)
        if self.magic != 0xFAB11BAF:
            raise MetadataParseError(
                f"unexpected metadata magic 0x{self.magic:08x} "
                "(expected 0xFAB11BAF)"
            )
        if self.version >= 38:
            raise MetadataParseError(
                "metadata versions >= 38 use newer dynamic index/header "
                "layouts; this lightweight parser currently supports v29-v37"
            )
        if self.version < 29:
            raise MetadataParseError(
                "this parser is focused on Endfield's v29+ metadata layout"
            )

        self.sections = self._parse_sections()
        self._string_cache: dict[int, str] = {}
        self._full_name_cache: dict[int, str] = {}
        self.type_record_size = self._type_record_size()
        self.method_record_size = self._method_record_size()
        self.field_record_size = 12
        self.parameter_record_size = 12
        self.image_record_size = 40

        self.types = self._parse_types()
        self.methods = self._parse_methods()
        self.fields = self._parse_fields()
        self.parameters = self._parse_parameters()
        self.images = self._parse_images()
        self.nested_parent_by_type_index = self._parse_nested_parents()
        self.image_name_by_type_index = self._map_images_to_types()
        self.type_name_by_metadata_type_index = self._map_metadata_type_names()

    def _parse_sections(self) -> dict[str, Section]:
        names = [
            "stringLiteral",
            "stringLiteralData",
            "string",
            "events",
            "properties",
            "methods",
            "parameterDefaultValues",
            "fieldDefaultValues",
            "fieldAndParameterDefaultValueData",
            "fieldMarshaledSizes",
            "parameters",
            "fields",
            "genericParameters",
            "genericParameterConstraints",
            "genericContainers",
            "nestedTypes",
            "interfaces",
            "vtableMethods",
            "interfaceOffsets",
            "typeDefinitions",
            "images",
            "assemblies",
            "fieldRefs",
            "referencedAssemblies",
            "attributeData",
            "attributeDataRange",
            "unresolvedVirtualCallParameterTypes",
            "unresolvedVirtualCallParameterRanges",
            "windowsRuntimeTypeNames",
            "windowsRuntimeStrings",
            "exportedTypeDefinitions",
        ]
        offset = 8
        sections: dict[str, Section] = {}
        for name in names:
            raw_offset, raw_size = struct.unpack_from("<Ii", self.buf, offset)
            sections[name] = Section(name, raw_offset, raw_size)
            offset += 8
        return sections

    def _type_record_size(self) -> int:
        section_size = self.sections["typeDefinitions"].size
        # Endfield's v29 metadata keeps byrefTypeIndex, so the type record is
        # 92 bytes. It also uses the field/method/property start block before
        # flags. Some newer parsers describe a trimmed 88-byte v29 shape, so
        # infer the local stride instead of assuming one dialect.
        for size in (92, 88, 84):
            if section_size % size == 0:
                return size
        # Fall back to the common post-v35 shape to produce a useful alignment
        # warning before parsing fails loudly.
        return 84 if self.version >= 35 else 92

    def _method_record_size(self) -> int:
        # v31 added returnParameterToken.
        return 36 if self.version >= 31 else 32

    def string(self, index: int) -> str:
        if index < 0:
            return ""
        cached = self._string_cache.get(index)
        if cached is not None:
            return cached
        section = self.sections["string"]
        start = section.offset + index
        end_limit = section.offset + section.size
        if start < section.offset or start >= end_limit:
            return f"<bad-string-index:{index}>"
        end = self.buf.find(b"\x00", start, end_limit)
        if end < 0:
            end = end_limit
        value = self.buf[start:end].decode("utf-8", errors="replace")
        self._string_cache[index] = value
        return value

    def _parse_types(self) -> list[TypeDef]:
        section = self.sections["typeDefinitions"]
        self._warn_if_misaligned(section, self.type_record_size)
        out: list[TypeDef] = []
        for index in range(section.count(self.type_record_size)):
            pos = section.offset + index * self.type_record_size
            name_index = self._i32(pos)
            namespace_index = self._i32(pos + 4)
            pos += 8
            byval_type_index = self._i32(pos)
            pos += 4
            byref_type_index: int | None = None
            if self.type_record_size in (92,):
                byref_type_index = self._i32(pos)
                pos += 4
            declaring_type_index = self._i32(pos)
            parent_index = self._i32(pos + 4)
            pos += 8
            element_type_index: int | None = None
            if self.type_record_size in (88, 92):
                element_type_index = self._i32(pos)
                pos += 4
            generic_container_index = self._i32(pos)
            pos += 4
            starts = struct.unpack_from("<iiiiiiii", self.buf, pos)
            pos += 32
            flags = self._u32(pos)
            pos += 4
            counts = struct.unpack_from("<HHHHHHHH", self.buf, pos)
            pos += 16
            bitfield = self._u32(pos)
            token = self._u32(pos + 4)
            out.append(
                TypeDef(
                    index=index,
                    name_index=name_index,
                    namespace_index=namespace_index,
                    byval_type_index=byval_type_index,
                    byref_type_index=byref_type_index,
                    declaring_type_index=declaring_type_index,
                    parent_index=parent_index,
                    element_type_index=element_type_index,
                    generic_container_index=generic_container_index,
                    flags=flags,
                    field_start=starts[0],
                    method_start=starts[1],
                    event_start=starts[2],
                    property_start=starts[3],
                    nested_types_start=starts[4],
                    interfaces_start=starts[5],
                    vtable_start=starts[6],
                    interface_offsets_start=starts[7],
                    method_count=counts[0],
                    property_count=counts[1],
                    field_count=counts[2],
                    event_count=counts[3],
                    nested_type_count=counts[4],
                    vtable_count=counts[5],
                    interfaces_count=counts[6],
                    interface_offsets_count=counts[7],
                    bitfield=bitfield,
                    token=token,
                )
            )
        return out

    def _parse_methods(self) -> list[MethodDef]:
        section = self.sections["methods"]
        self._warn_if_misaligned(section, self.method_record_size)
        out: list[MethodDef] = []
        for index in range(section.count(self.method_record_size)):
            pos = section.offset + index * self.method_record_size
            name_index = self._i32(pos)
            declaring_type = self._i32(pos + 4)
            return_type = self._i32(pos + 8)
            pos += 12
            return_parameter_token = None
            if self.version >= 31:
                return_parameter_token = self._u32(pos)
                pos += 4
            parameter_start = self._i32(pos)
            generic_container_index = self._i32(pos + 4)
            token = self._u32(pos + 8)
            flags, iflags, slot, parameter_count = struct.unpack_from("<HHHH", self.buf, pos + 12)
            out.append(
                MethodDef(
                    index=index,
                    name_index=name_index,
                    declaring_type=declaring_type,
                    return_type=return_type,
                    return_parameter_token=return_parameter_token,
                    parameter_start=parameter_start,
                    generic_container_index=generic_container_index,
                    token=token,
                    flags=flags,
                    iflags=iflags,
                    slot=slot,
                    parameter_count=parameter_count,
                )
            )
        return out

    def _parse_fields(self) -> list[FieldDef]:
        section = self.sections["fields"]
        self._warn_if_misaligned(section, self.field_record_size)
        out: list[FieldDef] = []
        for index in range(section.count(self.field_record_size)):
            pos = section.offset + index * self.field_record_size
            out.append(
                FieldDef(
                    index=index,
                    name_index=self._i32(pos),
                    type_index=self._i32(pos + 4),
                    token=self._u32(pos + 8),
                )
            )
        return out

    def _parse_parameters(self) -> list[ParameterDef]:
        section = self.sections["parameters"]
        self._warn_if_misaligned(section, self.parameter_record_size)
        out: list[ParameterDef] = []
        for index in range(section.count(self.parameter_record_size)):
            pos = section.offset + index * self.parameter_record_size
            out.append(
                ParameterDef(
                    index=index,
                    name_index=self._i32(pos),
                    token=self._u32(pos + 4),
                    type_index=self._i32(pos + 8),
                )
            )
        return out

    def _parse_images(self) -> list[ImageDef]:
        section = self.sections["images"]
        self._warn_if_misaligned(section, self.image_record_size)
        out: list[ImageDef] = []
        for index in range(section.count(self.image_record_size)):
            pos = section.offset + index * self.image_record_size
            values = struct.unpack_from("<iiiiIiiIiI", self.buf, pos)
            out.append(
                ImageDef(
                    index=index,
                    name_index=values[0],
                    assembly_index=values[1],
                    type_start=values[2],
                    type_count=values[3],
                    exported_type_start=values[4],
                    exported_type_count=values[5],
                    entry_point_index=values[6],
                    token=values[7],
                    custom_attribute_start=values[8],
                    custom_attribute_count=values[9],
                )
            )
        return out

    def _parse_nested_parents(self) -> dict[int, int]:
        section = self.sections["nestedTypes"]
        parents: dict[int, int] = {}
        for parent in self.types:
            if parent.nested_type_count <= 0 or parent.nested_types_start < 0:
                continue
            for rel in range(parent.nested_type_count):
                pos = section.offset + (parent.nested_types_start + rel) * 4
                if pos < section.offset or pos + 4 > section.offset + section.size:
                    continue
                child_idx = self._i32(pos)
                if 0 <= child_idx < len(self.types):
                    parents[child_idx] = parent.index
        return parents

    def _map_images_to_types(self) -> dict[int, str]:
        mapping: dict[int, str] = {}
        for image in self.images:
            image_name = self.string(image.name_index)
            for idx in range(image.type_start, image.type_start + image.type_count):
                if 0 <= idx < len(self.types):
                    mapping[idx] = image_name
        return mapping

    def _map_metadata_type_names(self) -> dict[int, str]:
        mapping: dict[int, str] = {}
        for type_def in self.types:
            full_name = self.type_full_name(type_def)
            if type_def.byval_type_index >= 0:
                mapping.setdefault(type_def.byval_type_index, full_name)
            if type_def.byref_type_index is not None and type_def.byref_type_index >= 0:
                mapping.setdefault(type_def.byref_type_index, f"{full_name}&")
        return mapping

    def metadata_type_name(self, type_index: int) -> str:
        if type_index < 0:
            return ""
        return self.type_name_by_metadata_type_index.get(type_index, f"<type-index:{type_index}>")

    def type_name(self, type_def: TypeDef) -> str:
        return self.string(type_def.name_index)

    def type_namespace(self, type_def: TypeDef) -> str:
        return self.string(type_def.namespace_index)

    def type_full_name(self, type_def: TypeDef, seen: set[int] | None = None) -> str:
        if seen is None:
            cached = self._full_name_cache.get(type_def.index)
            if cached is not None:
                return cached
        if seen is None:
            seen = set()
        if type_def.index in seen:
            return self.type_name(type_def)
        seen.add(type_def.index)

        name = self.type_name(type_def)
        parent_idx = self.nested_parent_by_type_index.get(type_def.index)
        if parent_idx is not None and 0 <= parent_idx < len(self.types):
            full_name = f"{self.type_full_name(self.types[parent_idx], seen)}+{name}"
            self._full_name_cache[type_def.index] = full_name
            return full_name
        namespace = self.type_namespace(type_def)
        full_name = f"{namespace}.{name}" if namespace else name
        self._full_name_cache[type_def.index] = full_name
        return full_name

    def fields_for(self, type_def: TypeDef) -> list[FieldDef]:
        if type_def.field_count <= 0 or type_def.field_start < 0:
            return []
        return self.fields[type_def.field_start:type_def.field_start + type_def.field_count]

    def methods_for(self, type_def: TypeDef) -> list[MethodDef]:
        if type_def.method_count <= 0 or type_def.method_start < 0:
            return []
        return self.methods[type_def.method_start:type_def.method_start + type_def.method_count]

    def parameters_for(self, method: MethodDef) -> list[ParameterDef]:
        if method.parameter_count <= 0 or method.parameter_start < 0:
            return []
        return self.parameters[method.parameter_start:method.parameter_start + method.parameter_count]

    def _warn_if_misaligned(self, section: Section, record_size: int) -> None:
        if section.size % record_size:
            print(
                f"warning: section {section.name} size {section.size} is not "
                f"aligned to record size {record_size}",
                file=sys.stderr,
            )

    def _i32(self, pos: int) -> int:
        return struct.unpack_from("<i", self.buf, pos)[0]

    def _u32(self, pos: int) -> int:
        return struct.unpack_from("<I", self.buf, pos)[0]


def resolve_metadata_path(explicit_path: Path | None, *, prefer_cache: bool) -> Path:
    if explicit_path is not None:
        if explicit_path.is_file():
            return explicit_path
        raise FileNotFoundError(f"metadata file not found: {explicit_path}")

    candidates = (
        (DEFAULT_CACHE_METADATA, DEFAULT_INSTALL_METADATA)
        if prefer_cache
        else (DEFAULT_INSTALL_METADATA, DEFAULT_CACHE_METADATA)
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(
        "No global-metadata.dat was found. Provide --metadata <path>, or recover "
        f"a validated copy into {DEFAULT_CACHE_METADATA} with --cache-metadata "
        "when a local source exists."
    )


def catalog_metadata_summary(md: Metadata) -> dict[str, Any]:
    return {
        "path": str(md.path),
        "size": len(md.buf),
        "sha256": hashlib.sha256(md.buf).hexdigest(),
        "version": md.version,
        "typeCount": len(md.types),
        "methodCount": len(md.methods),
        "fieldCount": len(md.fields),
        "parameterCount": len(md.parameters),
        "imageCount": len(md.images),
        "typeRecordSize": md.type_record_size,
        "methodRecordSize": md.method_record_size,
    }


def cache_metadata(source: Path, cache_path: Path) -> tuple[Path, dict[str, Any]]:
    source_md = Metadata(source)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    source_resolved = source.resolve()
    cache_resolved = cache_path.resolve()
    if source_resolved != cache_resolved:
        shutil.copy2(source, cache_path)

    cached_md = Metadata(cache_path)
    summary = {
        "source": str(source_resolved),
        "cache": str(cache_resolved),
        "metadata": catalog_metadata_summary(cached_md),
    }
    sidecar = cache_path.with_name(cache_path.stem + "_source.json")
    sidecar.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    if source_md.version != cached_md.version or len(source_md.buf) != len(cached_md.buf):
        raise MetadataParseError("cached metadata did not match the validated source")

    return cache_path, summary


def member_names(md: Metadata, type_def: TypeDef) -> tuple[list[str], list[str]]:
    fields = [md.string(field.name_index) for field in md.fields_for(type_def)]
    methods = [md.string(method.name_index) for method in md.methods_for(type_def)]
    return fields, methods


def matched_terms(pattern: re.Pattern[str], values: Iterable[str]) -> list[str]:
    hits = sorted({value for value in values if value and pattern.search(value)})
    return hits


def field_row(md: Metadata, field: FieldDef) -> dict[str, Any]:
    return {
        "index": field.index,
        "name": md.string(field.name_index),
        "typeIndex": field.type_index,
        "typeName": md.metadata_type_name(field.type_index),
        "token": f"0x{field.token:08x}",
    }


def parameter_row(md: Metadata, param: ParameterDef) -> dict[str, Any]:
    return {
        "index": param.index,
        "name": md.string(param.name_index),
        "typeIndex": param.type_index,
        "typeName": md.metadata_type_name(param.type_index),
        "token": f"0x{param.token:08x}",
    }


def method_row(md: Metadata, method: MethodDef) -> dict[str, Any]:
    param_rows = [parameter_row(md, param) for param in md.parameters_for(method)]
    return {
        "index": method.index,
        "name": md.string(method.name_index),
        "parameterCount": method.parameter_count,
        "parameters": [param["name"] for param in param_rows],
        "parameterDetails": param_rows,
        "returnTypeIndex": method.return_type,
        "returnTypeName": md.metadata_type_name(method.return_type),
        "token": f"0x{method.token:08x}",
        "flags": f"0x{method.flags:04x}",
        "iflags": f"0x{method.iflags:04x}",
        "slot": method.slot,
    }


def is_unresolved_type_name(type_name: str) -> bool:
    return type_name.startswith("<type-index:")


def add_type_index_usage(
    usages: dict[int, dict[str, Any]],
    *,
    type_index: int,
    type_name: str,
    owner: str,
    member_kind: str,
    member_name: str,
    token: str,
) -> None:
    if type_index < 0 or not is_unresolved_type_name(type_name):
        return
    row = usages.setdefault(
        type_index,
        {
            "typeIndex": type_index,
            "typeName": type_name,
            "uses": [],
        },
    )
    row["uses"].append(
        {
            "owner": owner,
            "memberKind": member_kind,
            "memberName": member_name,
            "token": token,
        }
    )


def collect_unresolved_type_index_usages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usages: dict[int, dict[str, Any]] = {}
    for owner in rows:
        owner_name = owner["fullName"]
        for field in owner.get("fields", []):
            add_type_index_usage(
                usages,
                type_index=field["typeIndex"],
                type_name=field["typeName"],
                owner=owner_name,
                member_kind="field",
                member_name=field["name"],
                token=field["token"],
            )
        for method in owner.get("methods", []):
            add_type_index_usage(
                usages,
                type_index=method["returnTypeIndex"],
                type_name=method["returnTypeName"],
                owner=owner_name,
                member_kind="methodReturn",
                member_name=method["name"],
                token=method["token"],
            )
            for param in method.get("parameterDetails", []):
                add_type_index_usage(
                    usages,
                    type_index=param["typeIndex"],
                    type_name=param["typeName"],
                    owner=owner_name,
                    member_kind="methodParameter",
                    member_name=f"{method['name']}({param['name']})",
                    token=method["token"],
                )
    out = list(usages.values())
    for row in out:
        row["uses"].sort(key=lambda use: (use["owner"], use["memberKind"], use["memberName"]))
    out.sort(key=lambda row: (-len(row["uses"]), row["typeIndex"]))
    return out


def summarize_type(
    md: Metadata,
    type_def: TypeDef,
    member_re: re.Pattern[str],
    *,
    include_all_members: bool,
) -> dict[str, Any]:
    full_name = md.type_full_name(type_def)
    simple_name = md.type_name(type_def)
    namespace = md.type_namespace(type_def)

    field_rows = []
    for field in md.fields_for(type_def):
        row = field_row(md, field)
        name = row["name"]
        if include_all_members or member_re.search(name):
            field_rows.append(row)

    method_rows = []
    for method in md.methods_for(type_def):
        row = method_row(md, method)
        name = row["name"]
        param_names = row["parameters"]
        signature_text = f"{name}({', '.join(param_names)})"
        if include_all_members or member_re.search(name) or member_re.search(signature_text):
            method_rows.append(row)

    return {
        "index": type_def.index,
        "fullName": full_name,
        "name": simple_name,
        "namespace": namespace,
        "image": md.image_name_by_type_index.get(type_def.index, ""),
        "token": f"0x{type_def.token:08x}",
        "fieldStart": type_def.field_start,
        "fieldCount": type_def.field_count,
        "methodStart": type_def.method_start,
        "methodCount": type_def.method_count,
        "fields": field_rows,
        "methods": method_rows,
    }


def build_catalog(
    md: Metadata,
    type_re: re.Pattern[str],
    member_re: re.Pattern[str],
    body_target_re: re.Pattern[str],
    body_target_type_re: re.Pattern[str] | None,
    image_re: re.Pattern[str] | None,
    *,
    only_focus: bool,
    include_all_members: bool,
    body_context: int,
) -> dict[str, Any]:
    matched: list[dict[str, Any]] = []
    focus: list[dict[str, Any]] = []
    member_only: list[dict[str, Any]] = []
    group_counts: Counter[str] = Counter()

    for type_def in md.types:
        image_name = md.image_name_by_type_index.get(type_def.index, "")
        if image_re is not None and not image_re.search(image_name):
            continue
        full_name = md.type_full_name(type_def)
        simple_name = md.type_name(type_def)
        field_names, method_names = member_names(md, type_def)
        type_hit = bool(type_re.search(full_name) or simple_name in FOCUS_TYPE_NAMES)
        field_hits = matched_terms(member_re, field_names)
        method_hits = matched_terms(member_re, method_names)
        has_member_hit = bool(field_hits or method_hits)
        is_focus = simple_name in FOCUS_TYPE_NAMES or full_name in FOCUS_TYPE_NAMES

        if not type_hit and not has_member_hit:
            continue
        if only_focus and not is_focus:
            continue

        row = summarize_type(
            md,
            type_def,
            member_re,
            include_all_members=include_all_members or is_focus,
        )
        row["matchedBy"] = {
            "typeName": type_hit,
            "focusName": is_focus,
            "fieldNames": field_hits,
            "methodNames": method_hits,
        }
        matched.append(row)

        if is_focus:
            focus.append(row)
        elif not type_hit and has_member_hit:
            member_only.append(row)

        for label, pattern in [
            ("option", re.compile("option", re.IGNORECASE)),
            ("timeline", re.compile("timeline", re.IGNORECASE)),
            ("tree", re.compile("tree", re.IGNORECASE)),
            ("trunk", re.compile("trunk", re.IGNORECASE)),
            ("jump", re.compile("jump", re.IGNORECASE)),
            ("playable", re.compile("playable", re.IGNORECASE)),
        ]:
            if pattern.search(full_name) or any(pattern.search(v) for v in field_hits + method_hits):
                group_counts[label] += 1

    matched.sort(key=lambda r: (not r["matchedBy"]["focusName"], r["fullName"]))
    focus.sort(key=lambda r: r["fullName"])
    member_only.sort(key=lambda r: r["fullName"])
    if body_target_type_re is not None:
        body_target_rows = [
            row
            for row in matched
            if body_target_type_re.search(row["fullName"])
            or body_target_type_re.search(row["name"])
        ]
    else:
        body_target_rows = focus or matched
    body_targets = collect_body_targets(
        md,
        body_target_rows,
        body_target_re,
        context=max(0, body_context),
    )
    unresolved_type_index_usages = collect_unresolved_type_index_usages(focus or matched)

    return {
        "metadata": catalog_metadata_summary(md),
        "settings": {
            "typeRegex": type_re.pattern,
            "memberRegex": member_re.pattern,
            "bodyTargetRegex": body_target_re.pattern,
            "bodyTargetTypeRegex": (
                body_target_type_re.pattern if body_target_type_re is not None else None
            ),
            "bodyContext": max(0, body_context),
            "imageRegex": image_re.pattern if image_re is not None else None,
            "onlyFocus": only_focus,
            "includeAllMembers": include_all_members,
        },
        "summary": {
            "matchedTypeCount": len(matched),
            "focusTypeCount": len(focus),
            "memberOnlyTypeCount": len(member_only),
            "bodyTargetMethodCount": len(body_targets),
            "unresolvedTypeIndexCount": len(unresolved_type_index_usages),
            "groupCounts": dict(sorted(group_counts.items())),
        },
        "bodyTargets": body_targets,
        "unresolvedTypeIndexUsages": unresolved_type_index_usages,
        "focusTypes": focus,
        "memberOnlyTypes": member_only,
        "matchedTypes": matched,
    }


def collect_body_targets(
    md: Metadata,
    rows: list[dict[str, Any]],
    body_target_re: re.Pattern[str],
    *,
    context: int,
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for row in rows:
        type_index = row.get("index", -1)
        if not 0 <= type_index < len(md.types):
            continue
        type_def = md.types[type_index]
        methods = md.methods_for(type_def)
        type_fields = [field_row(md, field) for field in md.fields_for(type_def)]
        for offset, method in enumerate(methods):
            current = method_row(md, method)
            if not body_target_re.search(current["name"]):
                continue
            start = max(0, offset - context)
            end = min(len(methods), offset + context + 1)
            method_neighborhood = []
            for neighbor_offset in range(start, end):
                neighbor = method_row(md, methods[neighbor_offset])
                neighbor["relativeOffset"] = neighbor_offset - offset
                neighbor["isTarget"] = neighbor_offset == offset
                method_neighborhood.append(neighbor)
            targets.append(
                {
                    "type": row["fullName"],
                    "image": row["image"],
                    "typeIndex": row["index"],
                    "typeToken": row["token"],
                    "method": current["name"],
                    "methodIndex": current["index"],
                    "methodOffsetInType": offset,
                    "token": current["token"],
                    "parameters": current["parameters"],
                    "parameterDetails": current["parameterDetails"],
                    "returnTypeIndex": current["returnTypeIndex"],
                    "returnTypeName": current["returnTypeName"],
                    "flags": current["flags"],
                    "iflags": current["iflags"],
                    "slot": current["slot"],
                    "typeFields": type_fields,
                    "methodNeighborhood": method_neighborhood,
                }
            )
    targets.sort(key=lambda r: (r["type"], r["method"], r["methodIndex"]))
    return targets


def compact_member_names(row: dict[str, Any], key: str, cap: int) -> str:
    names = [item["name"] for item in row.get(key, [])]
    if not names:
        return "-"
    if len(names) > cap:
        return ", ".join(names[:cap]) + f", ... (+{len(names) - cap})"
    return ", ".join(names)


def compact_field_details(fields: list[dict[str, Any]], cap: int) -> str:
    if not fields:
        return "-"
    parts = [
        f"{field['name']}:{field.get('typeName') or field.get('typeIndex')}"
        for field in fields[:cap]
    ]
    if len(fields) > cap:
        parts.append(f"... (+{len(fields) - cap})")
    return ", ".join(parts)


def format_method_signature(row: dict[str, Any], *, typed: bool) -> str:
    if typed:
        params = [
            f"{param['name']}:{param.get('typeName') or param.get('typeIndex')}"
            for param in row.get("parameterDetails", [])
        ]
    else:
        params = row.get("parameters") or []
    return f"{row['method']}({', '.join(params)})"


def compact_method_neighborhood(rows: list[dict[str, Any]], cap: int) -> str:
    if not rows:
        return "-"
    parts = []
    for row in rows[:cap]:
        prefix = "target" if row.get("isTarget") else f"{row.get('relativeOffset', 0):+d}"
        params = ", ".join(row.get("parameters") or [])
        parts.append(f"{prefix}:{row['name']}({params})")
    if len(rows) > cap:
        parts.append(f"... (+{len(rows) - cap})")
    return "; ".join(parts)


def write_markdown(path: Path, catalog: dict[str, Any], *, cap: int) -> None:
    meta = catalog["metadata"]
    summary = catalog["summary"]
    lines = [
        "# Dialog Option Flow Runtime Metadata",
        "",
        f"Metadata: `{meta['path']}`",
        "",
        f"- version: {meta['version']}",
        f"- size: {meta['size']:,} bytes",
        f"- sha256: `{meta['sha256']}`",
        f"- type definitions: {meta['typeCount']:,}",
        f"- methods: {meta['methodCount']:,}",
        f"- fields: {meta['fieldCount']:,}",
        f"- matched types: {summary['matchedTypeCount']:,}",
        f"- focus types: {summary['focusTypeCount']:,}",
        f"- member-only types: {summary['memberOnlyTypeCount']:,}",
        f"- likely method-body targets: {summary['bodyTargetMethodCount']:,}",
        f"- unresolved type indexes: {summary['unresolvedTypeIndexCount']:,}",
        "",
        "## Group Counts",
        "",
    ]
    for key, value in summary["groupCounts"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## Likely Method-Body Targets",
            "",
        ]
    )
    if not catalog["bodyTargets"]:
        lines.append("- none")
    else:
        for row in catalog["bodyTargets"][:cap * 2]:
            signature = format_method_signature(row, typed=True)
            return_type = row.get("returnTypeName") or row.get("returnTypeIndex")
            lines.append(
                f"- `{return_type} {row['type']}.{signature}` "
                f"methodIndex={row['methodIndex']} offset={row.get('methodOffsetInType')} "
                f"token=`{row['token']}`"
            )
            lines.append(
                f"  - type fields: {compact_field_details(row.get('typeFields', []), cap=12)}"
            )
            lines.append(
                "  - method neighbors: "
                + compact_method_neighborhood(row.get("methodNeighborhood", []), cap=12)
            )
        if len(catalog["bodyTargets"]) > cap * 2:
            lines.append(f"- ... and {len(catalog['bodyTargets']) - cap * 2} more")

    lines.extend(
        [
            "",
            "## Unresolved Type Index Uses",
            "",
        ]
    )
    if not catalog["unresolvedTypeIndexUsages"]:
        lines.append("- none")
    else:
        for row in catalog["unresolvedTypeIndexUsages"][:cap]:
            uses = [
                f"{use['owner']}.{use['memberName']} [{use['memberKind']}]"
                for use in row["uses"][:8]
            ]
            suffix = ""
            if len(row["uses"]) > 8:
                suffix = f"; ... (+{len(row['uses']) - 8})"
            lines.append(
                f"- `{row['typeName']}` uses={len(row['uses'])}: "
                + "; ".join(uses)
                + suffix
            )
        if len(catalog["unresolvedTypeIndexUsages"]) > cap:
            lines.append(
                f"- ... and {len(catalog['unresolvedTypeIndexUsages']) - cap} more"
            )

    lines.extend(
        [
            "",
            "## Focus Types",
            "",
        ]
    )
    if not catalog["focusTypes"]:
        lines.append("- none")
    else:
        for row in catalog["focusTypes"]:
            lines.extend(render_type_block(row, cap=cap))

    lines.extend(
        [
            "",
            "## Top Matched Types",
            "",
        ]
    )
    for row in catalog["matchedTypes"][:cap]:
        if row in catalog["focusTypes"]:
            continue
        lines.extend(render_type_block(row, cap=max(8, cap // 2)))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def type_member_signature(row: dict[str, Any]) -> dict[str, set[str]]:
    return {
        "fields": {field["name"] for field in row.get("fields", [])},
        "methods": {method["name"] for method in row.get("methods", [])},
    }


def body_target_key(row: dict[str, Any]) -> str:
    params = ",".join(row.get("parameters") or [])
    return f"{row.get('type')}::{row.get('method')}({params})::{row.get('token')}"


def build_catalog_diff(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if previous is None:
        return {
            "summary": {
                "hasPrevious": False,
                "hasChanges": False,
                "message": "No previous runtime metadata report was available.",
            },
            "metadata": {
                "previous": None,
                "current": current.get("metadata", {}),
            },
            "focusTypeChanges": [],
            "bodyTargetChanges": {"added": [], "removed": []},
            "summaryChanges": {},
        }

    prev_summary = previous.get("summary", {})
    curr_summary = current.get("summary", {})
    summary_changes = {
        key: {"previous": prev_summary.get(key), "current": curr_summary.get(key)}
        for key in sorted(set(prev_summary) | set(curr_summary))
        if prev_summary.get(key) != curr_summary.get(key)
    }

    prev_focus = {row["fullName"]: row for row in previous.get("focusTypes", [])}
    curr_focus = {row["fullName"]: row for row in current.get("focusTypes", [])}
    focus_changes = []
    for name in sorted(set(prev_focus) | set(curr_focus)):
        if name not in prev_focus:
            focus_changes.append({"type": name, "change": "added"})
            continue
        if name not in curr_focus:
            focus_changes.append({"type": name, "change": "removed"})
            continue
        prev_members = type_member_signature(prev_focus[name])
        curr_members = type_member_signature(curr_focus[name])
        field_added = sorted(curr_members["fields"] - prev_members["fields"])
        field_removed = sorted(prev_members["fields"] - curr_members["fields"])
        method_added = sorted(curr_members["methods"] - prev_members["methods"])
        method_removed = sorted(prev_members["methods"] - curr_members["methods"])
        if field_added or field_removed or method_added or method_removed:
            focus_changes.append(
                {
                    "type": name,
                    "change": "membersChanged",
                    "fieldsAdded": field_added,
                    "fieldsRemoved": field_removed,
                    "methodsAdded": method_added,
                    "methodsRemoved": method_removed,
                }
            )

    prev_targets = {body_target_key(row): row for row in previous.get("bodyTargets", [])}
    curr_targets = {body_target_key(row): row for row in current.get("bodyTargets", [])}
    added_targets = [curr_targets[key] for key in sorted(set(curr_targets) - set(prev_targets))]
    removed_targets = [prev_targets[key] for key in sorted(set(prev_targets) - set(curr_targets))]

    has_changes = bool(summary_changes or focus_changes or added_targets or removed_targets)
    return {
        "summary": {
            "hasPrevious": True,
            "hasChanges": has_changes,
            "focusTypeChangeCount": len(focus_changes),
            "bodyTargetsAdded": len(added_targets),
            "bodyTargetsRemoved": len(removed_targets),
            "summaryChangeCount": len(summary_changes),
        },
        "metadata": {
            "previous": previous.get("metadata", {}),
            "current": current.get("metadata", {}),
        },
        "focusTypeChanges": focus_changes,
        "bodyTargetChanges": {
            "added": added_targets,
            "removed": removed_targets,
        },
        "summaryChanges": summary_changes,
    }


def write_diff_markdown(path: Path, diff: dict[str, Any]) -> None:
    summary = diff["summary"]
    lines = [
        "# Dialog Option Flow Runtime Metadata Diff",
        "",
    ]
    if not summary.get("hasPrevious"):
        lines.extend(
            [
                "No previous runtime metadata report was available.",
                "",
                "The current run is now the comparison baseline for the next export.",
            ]
        )
    elif not summary.get("hasChanges"):
        lines.append("No option-flow runtime metadata drift detected against the previous report.")
    else:
        lines.extend(
            [
                "- summary changes: " + str(summary.get("summaryChangeCount", 0)),
                "- focus type changes: " + str(summary.get("focusTypeChangeCount", 0)),
                "- body targets added: " + str(summary.get("bodyTargetsAdded", 0)),
                "- body targets removed: " + str(summary.get("bodyTargetsRemoved", 0)),
                "",
            ]
        )
        if diff.get("summaryChanges"):
            lines.append("## Summary Changes")
            lines.append("")
            for key, values in diff["summaryChanges"].items():
                lines.append(f"- `{key}`: {values['previous']} -> {values['current']}")
            lines.append("")
        if diff.get("focusTypeChanges"):
            lines.append("## Focus Type Changes")
            lines.append("")
            for row in diff["focusTypeChanges"]:
                lines.append(f"- `{row['type']}`: {row['change']}")
                for key in ("fieldsAdded", "fieldsRemoved", "methodsAdded", "methodsRemoved"):
                    values = row.get(key) or []
                    if values:
                        lines.append(f"  - {key}: {', '.join(values)}")
            lines.append("")
        body_changes = diff.get("bodyTargetChanges", {})
        if body_changes.get("added"):
            lines.append("## Body Targets Added")
            lines.append("")
            for row in body_changes["added"]:
                params = ", ".join(row.get("parameters") or [])
                lines.append(f"- `{row['type']}.{row['method']}({params})` `{row['token']}`")
            lines.append("")
        if body_changes.get("removed"):
            lines.append("## Body Targets Removed")
            lines.append("")
            for row in body_changes["removed"]:
                params = ", ".join(row.get("parameters") or [])
                lines.append(f"- `{row['type']}.{row['method']}({params})` `{row['token']}`")
            lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def render_type_block(row: dict[str, Any], *, cap: int) -> list[str]:
    field_text = compact_member_names(row, "fields", cap)
    method_text = compact_member_names(row, "methods", cap)
    matched_by = row.get("matchedBy", {})
    flags = []
    if matched_by.get("focusName"):
        flags.append("focus")
    if matched_by.get("typeName"):
        flags.append("type")
    if matched_by.get("fieldNames"):
        flags.append(f"fields={len(matched_by['fieldNames'])}")
    if matched_by.get("methodNames"):
        flags.append(f"methods={len(matched_by['methodNames'])}")
    flag_text = ", ".join(flags) if flags else "match"
    return [
        f"### `{row['fullName']}`",
        "",
        f"- image: `{row['image']}`",
        f"- type index: {row['index']}; token: `{row['token']}`; match: {flag_text}",
        f"- fields ({row['fieldCount']} total, shown {len(row['fields'])}): {field_text}",
        f"- methods ({row['methodCount']} total, shown {len(row['methods'])}): {method_text}",
        "",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--metadata",
        type=Path,
        default=None,
        help=(
            "Path to global-metadata.dat. Defaults to the recovered cache if it "
            "exists, then the local Endfield install path. With --cache-metadata, "
            "the install path is preferred so update refreshes pick up new data."
        ),
    )
    parser.add_argument(
        "--cache-metadata",
        action="store_true",
        help=(
            "Validate the selected metadata file and copy it to the recovered "
            "cache before cataloging it."
        ),
    )
    parser.add_argument(
        "--cache-out",
        type=Path,
        default=DEFAULT_CACHE_METADATA,
        help="Recovered metadata cache path used by --cache-metadata.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument(
        "--type-regex",
        default=DEFAULT_TYPE_RE.pattern,
        help="Regex for matching type full names.",
    )
    parser.add_argument(
        "--member-regex",
        default=DEFAULT_MEMBER_RE.pattern,
        help="Regex for matching field/method/parameter names.",
    )
    parser.add_argument(
        "--body-target-regex",
        default=BODY_TARGET_METHOD_RE.pattern,
        help="Regex for method names to promote as likely GameAssembly body targets.",
    )
    parser.add_argument(
        "--body-target-type-regex",
        default=None,
        help=(
            "Optional regex for matched type full/simple names to consider for "
            "body targets. When omitted, the historical focus-or-matched type "
            "selection is used."
        ),
    )
    parser.add_argument(
        "--body-context",
        type=int,
        default=DEFAULT_BODY_CONTEXT,
        help="Neighbor method count to include before/after each body target.",
    )
    parser.add_argument(
        "--image-regex",
        default=DEFAULT_IMAGE_RE.pattern,
        help="Regex for assembly image names to include (default: Beyond assemblies).",
    )
    parser.add_argument(
        "--all-images",
        action="store_true",
        help="Do not filter by assembly image name.",
    )
    parser.add_argument(
        "--only-focus",
        action="store_true",
        help="Emit only known focus type names.",
    )
    parser.add_argument(
        "--include-all-members",
        action="store_true",
        help="Include all members for every matched type instead of only matching members.",
    )
    parser.add_argument(
        "--markdown-cap",
        type=int,
        default=40,
        help="Maximum type/member rows to show in markdown sections.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.only_focus:
        if args.out == DEFAULT_JSON:
            args.out = args.out.with_name("option_flow_runtime_metadata_focus.json")
        if args.markdown == DEFAULT_MD:
            args.markdown = args.markdown.with_name("option_flow_runtime_metadata_focus.md")

    metadata_path = resolve_metadata_path(args.metadata, prefer_cache=not args.cache_metadata)
    cache_summary = None
    if args.cache_metadata:
        metadata_path, cache_summary = cache_metadata(metadata_path, args.cache_out)

    type_re = re.compile(args.type_regex, re.IGNORECASE)
    member_re = re.compile(args.member_regex, re.IGNORECASE)
    body_target_re = re.compile(args.body_target_regex, re.IGNORECASE)
    body_target_type_re = (
        re.compile(args.body_target_type_regex, re.IGNORECASE)
        if args.body_target_type_regex
        else None
    )
    image_re = None if args.all_images else re.compile(args.image_regex, re.IGNORECASE)

    md = Metadata(metadata_path)
    catalog = build_catalog(
        md,
        type_re,
        member_re,
        body_target_re,
        body_target_type_re,
        image_re,
        only_focus=args.only_focus,
        include_all_members=args.include_all_members,
        body_context=args.body_context,
    )

    previous_catalog = None
    if args.out.is_file():
        try:
            previous_catalog = json.loads(args.out.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous_catalog = None
    diff = build_catalog_diff(previous_catalog, catalog)
    diff_json = args.out.with_name(args.out.stem + "_diff.json")
    diff_md = args.markdown.with_name(args.markdown.stem + "_diff.md")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(args.markdown, catalog, cap=args.markdown_cap)
    diff_json.write_text(json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")
    write_diff_markdown(diff_md, diff)

    meta = catalog["metadata"]
    summary = catalog["summary"]
    print(f"metadata: {metadata_path}")
    if cache_summary is not None:
        print(f"cached metadata: {cache_summary['cache']}")
        print(f"cache source: {cache_summary['source']}")
    print(f"  version={meta['version']} size={meta['size']:,}")
    print(f"  sha256={meta['sha256']}")
    print(f"  types={meta['typeCount']:,} methods={meta['methodCount']:,} fields={meta['fieldCount']:,}")
    print(f"matched types: {summary['matchedTypeCount']:,}")
    print(f"focus types: {summary['focusTypeCount']:,}")
    print(f"member-only types: {summary['memberOnlyTypeCount']:,}")
    print(f"wrote JSON: {args.out}")
    print(f"wrote Markdown: {args.markdown}")
    print(f"wrote diff JSON: {diff_json}")
    print(f"wrote diff Markdown: {diff_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
