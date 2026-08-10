#!/usr/bin/env python3
"""Recover reusable native contracts for serialized DialogTree controls.

The recovery is family-driven rather than content-driven.  A family spec names
managed schema members (node type, selector enum, serialized selector path,
and static port-map field); the implementation derives method pointers, enum
values, named port order, and the external-index continuation path from the
installed IL2CPP metadata and GameAssembly.  Mission ids, Story keys, object
ids, OCR, and manual overrides are never inputs.

The current consumer uses this for ``DialogTreeOpenUINode``.  The decoder is
kept generic so another node family with a static
``Dictionary<enum,List<string>>`` port contract can use the same validation and
corpus projection.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
MAPPER_PATH = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
CATALOG_PATH = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
DEFAULT_GAME_ROOT = Path(os.environ.get(
    "ENDFIELD_GAME_ROOT",
    r"D:\Program Files\Endfield Game\Endfield_Data",
))
DEFAULT_GAME_ASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
DEFAULT_IFIX_AUDIT = ROOT / "reports" / "story" / "recovery" / "current_ifix_mission_graph_audit.json"
MAX_METHOD_BYTES = 0x10000

RUNTIME_PRIMITIVES = {
    0x01: "void", 0x02: "bool", 0x03: "char", 0x04: "sbyte",
    0x05: "byte", 0x06: "short", 0x07: "ushort", 0x08: "int",
    0x09: "uint", 0x0A: "long", 0x0B: "ulong", 0x0C: "float",
    0x0D: "double", 0x0E: "System.String", 0x18: "nint",
    0x19: "nuint", 0x1C: "object",
}


class ContractError(RuntimeError):
    """Raised when original inputs cannot satisfy a bounded native contract."""


@dataclass(frozen=True)
class StaticPortFamilySpec:
    family: str
    node_type: str
    selector_enum_type: str
    serialized_selector_path: tuple[str, ...]
    static_port_map_field: str
    node_action_method: str
    manager_type: str
    manager_action_method: str
    global_action_type: str
    global_action_method: str
    manager_next_method: str
    controller_type: str
    controller_next_method: str


OPEN_UI_FAMILY = StaticPortFamilySpec(
    family="dialog_tree_open_ui",
    node_type="Beyond.Gameplay.DialogTreeOpenUINode",
    selector_enum_type="Beyond.Gameplay.DialogEnums+DialogOpenUIType",
    serialized_selector_path=("_actionData", "panelType"),
    static_port_map_field="s_panelOutConnections",
    node_action_method="DoAction",
    manager_type="Beyond.Gameplay.Core.DialogManager",
    manager_action_method="OpenUI",
    global_action_type="Beyond.Gameplay.Actions.GameAction",
    global_action_method="DialogOpenUIPanel",
    manager_next_method="Next",
    controller_type="Beyond.Gameplay.DialogTreeController",
    controller_next_method="Next",
)


_CONTRACT_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"cannot load required helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path.resolve())


def _read_compressed_uint32(data: bytes, offset: int) -> tuple[int, int]:
    first = data[offset]
    if first < 0x80:
        return first, 1
    if first < 0xC0:
        return ((first & 0x3F) << 8) | data[offset + 1], 2
    if first < 0xE0:
        return (
            ((first & 0x1F) << 16) | (data[offset + 1] << 8) | data[offset + 2],
            3,
        )
    if first < 0xF0:
        return (
            ((first & 0x0F) << 24)
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
    raise ContractError(f"unsupported compressed integer prefix 0x{first:02x}")


def _read_compressed_int32(data: bytes, offset: int) -> int:
    unsigned, _size = _read_compressed_uint32(data, offset)
    return (unsigned >> 1) ^ -(unsigned & 1)


def _runtime_type_name(
    pe: Any,
    metadata: Any,
    type_va: int,
    *,
    depth: int = 0,
    seen: frozenset[int] = frozenset(),
) -> str:
    """Decode one installed Il2CppType, including generic instances."""
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
        definition_va, class_inst_va = struct.unpack_from(
            "<QQ", pe.buf, generic_offset
        )
        definition = _runtime_type_name(
            pe,
            metadata,
            definition_va,
            depth=depth + 1,
            seen=seen | {type_va},
        )
        if not class_inst_va:
            return definition
        count = pe.u32_at_va(class_inst_va)
        argv = pe.u64_at_va(class_inst_va + 8)
        if count > 64:
            return f"{definition}<invalid-argc:{count}>"
        arguments = [
            _runtime_type_name(
                pe,
                metadata,
                pe.u64_at_va(argv + index * 8),
                depth=depth + 1,
                seen=seen | {type_va},
            )
            for index in range(count)
        ]
        return f"{definition}<{','.join(arguments)}>"
    return f"<runtime-type:0x{kind:x}>"


def _metadata_runtime_type_name(
    pe: Any,
    metadata: Any,
    mapper: Any,
    metadata_registration: int,
    metadata_type_index: int,
) -> str:
    summary = mapper.metadata_registration_summary(pe, metadata_registration)
    count = int(summary["typesCount"])
    if not 0 <= metadata_type_index < count:
        return f"<type-index:{metadata_type_index}>"
    types_va = int(summary["types"], 16)
    type_va = pe.u64_at_va(types_va + metadata_type_index * 8)
    return (
        _runtime_type_name(pe, metadata, type_va)
        if type_va
        else f"<type-index:{metadata_type_index}>"
    )


def _enum_members(metadata: Any, type_name: str) -> list[dict[str, Any]]:
    defaults: dict[int, int] = {}
    default_section = metadata.sections["fieldDefaultValues"]
    if default_section.size % 12:
        raise ContractError("fieldDefaultValues is not aligned to 12-byte records")
    for offset in range(
        default_section.offset,
        default_section.offset + default_section.size,
        12,
    ):
        field_index, _type_index, data_index = struct.unpack_from(
            "<iii", metadata.buf, offset
        )
        defaults[field_index] = data_index
    data_section = metadata.sections["fieldAndParameterDefaultValueData"]
    matches = [
        type_def
        for type_def in metadata.types
        if metadata.type_full_name(type_def) == type_name
    ]
    if len(matches) != 1:
        raise ContractError(f"expected one enum {type_name}, found {len(matches)}")
    members: list[dict[str, Any]] = []
    for field in metadata.fields_for(matches[0]):
        name = metadata.string(field.name_index)
        if name == "value__" or field.index not in defaults:
            continue
        members.append({
            "value": _read_compressed_int32(
                metadata.buf,
                data_section.offset + defaults[field.index],
            ),
            "name": name,
            "fieldIndex": field.index,
            "token": f"0x{field.token:08x}",
        })
    return sorted(members, key=lambda row: (row["value"], row["name"]))


def _method_rows(metadata: Any, type_name: str, method_name: str) -> list[Any]:
    rows: list[Any] = []
    for type_def in metadata.types:
        if metadata.type_full_name(type_def) != type_name:
            continue
        for method in metadata.methods_for(type_def):
            if metadata.string(method.name_index) == method_name:
                rows.append(method)
    return rows


def _method_pointer(
    method: Any,
    *,
    metadata: Any,
    mapper: Any,
    ranges: dict[str, dict[str, int]],
    pointers_by_image: dict[str, list[int]],
    generic_index: dict[int, list[dict[str, Any]]],
) -> tuple[int, str]:
    method_index = int(method.index)
    image = next(
        (
            image_name
            for image_name, image_range in ranges.items()
            if image_range["methodStart"] <= method_index < image_range["methodEnd"]
        ),
        "",
    )
    if not image:
        raise ContractError(f"method {method_index} has no codegen image")
    pointer = pointers_by_image[image][method_index - ranges[image]["methodStart"]]
    if pointer:
        return pointer, "codegen_module"
    candidates = mapper.generic_body_candidates(generic_index, method_index)
    if len(candidates) != 1:
        raise ContractError(
            f"method {method_index} has {len(candidates)} generic bodies"
        )
    return int(candidates[0]["methodPointerVa"], 16), "generic_method_pointer"


def _method_record(metadata: Any, method: Any, pointer: int, source: str) -> dict[str, Any]:
    owner = metadata.type_full_name(metadata.types[method.declaring_type])
    return {
        "type": owner,
        "method": metadata.string(method.name_index),
        "methodIndex": method.index,
        "token": f"0x{method.token:08x}",
        "address": f"0x{pointer:x}",
        "pointerSource": source,
    }


def _call_targets(instructions: Iterable[dict[str, Any]]) -> list[int]:
    targets: list[int] = []
    for row in instructions:
        match = re.fullmatch(r"call 0x([0-9a-f]+)", str(row.get("text") or ""))
        if match:
            targets.append(int(match.group(1), 16))
    return targets


def _decode_string_literal_handle(pe: Any, metadata: Any, slot_va: int) -> dict[str, Any]:
    """Decode the current-build tagged metadata handle stored at one slot.

    ``il2cpp_codegen_initialize_runtime_metadata`` extracts the kind from bits
    29..31 and the source index from ``(encoded >> 1) & 0x0fffffff``.  Kind 5
    addresses the global-metadata string-literal table.
    """
    encoded = pe.u64_at_va(slot_va)
    kind = encoded >> 29
    source_index = (encoded >> 1) & 0x0FFFFFFF
    result = {
        "slotVa": f"0x{slot_va:x}",
        "encodedHandle": f"0x{encoded:x}",
        "kind": kind,
        "sourceIndex": source_index,
    }
    if kind != 5:
        result["status"] = "not_string_literal"
        return result
    literal_section = metadata.sections["stringLiteral"]
    data_section = metadata.sections["stringLiteralData"]
    if source_index >= literal_section.size // 8:
        result["status"] = "string_literal_index_out_of_bounds"
        return result
    length, data_index = struct.unpack_from(
        "<II",
        metadata.buf,
        literal_section.offset + source_index * 8,
    )
    if data_index + length > data_section.size:
        result["status"] = "string_literal_data_out_of_bounds"
        return result
    result.update({
        "status": "decoded",
        "value": metadata.buf[
            data_section.offset + data_index:
            data_section.offset + data_index + length
        ].decode("utf-8", errors="replace"),
    })
    return result


def parse_static_enum_string_list_initializer(
    instructions: list[dict[str, Any]],
    *,
    dictionary_add_targets: set[int],
    decode_literal_slot: Any,
) -> list[dict[str, Any]]:
    """Parse repeated ``Dictionary.Add(enum, List<string>)`` initializer blocks.

    The parser depends only on calling convention and metadata-handle shape.
    It does not contain enum values, strings, method addresses, or content ids.
    """
    rows: list[dict[str, Any]] = []
    block_start = 0
    for call_index, instruction in enumerate(instructions):
        call_match = re.fullmatch(
            r"call 0x([0-9a-f]+)", str(instruction.get("text") or "")
        )
        if not call_match or int(call_match.group(1), 16) not in dictionary_add_targets:
            continue
        block = instructions[block_start:call_index]
        selector: int | None = None
        for row in reversed(block):
            text = str(row.get("text") or "")
            immediate = re.fullmatch(r"mov edx, 0x([0-9a-f]+)", text)
            if immediate:
                selector = int(immediate.group(1), 16)
                break
            if text == "xor edx, edx":
                selector = 0
                break
        labels: list[dict[str, Any]] = []
        for index, row in enumerate(block):
            slot_match = re.fullmatch(
                r"mov rdx, \[rip[+-]0x[0-9a-f]+ => 0x([0-9a-f]+)\]",
                str(row.get("text") or ""),
            )
            if not slot_match:
                continue
            # A string argument must feed a call before rdx is overwritten.
            has_call = False
            for follower in block[index + 1:index + 6]:
                follower_text = str(follower.get("text") or "")
                if follower_text.startswith(("mov rdx,", "xor edx,")):
                    break
                if follower_text.startswith("call 0x"):
                    has_call = True
                    break
            if not has_call:
                continue
            decoded = decode_literal_slot(int(slot_match.group(1), 16))
            if decoded.get("status") == "decoded":
                labels.append(decoded)
        if selector is None:
            raise ContractError(
                f"dictionary Add at {instruction.get('va')} has no enum selector"
            )
        if not labels:
            raise ContractError(
                f"dictionary Add at {instruction.get('va')} has no string labels"
            )
        rows.append({
            "selectorValue": selector,
            "labels": labels,
            "dictionaryAddCallVa": instruction.get("va"),
        })
        block_start = call_index + 1
    if not rows:
        raise ContractError("static initializer contains no enum/list dictionary rows")
    selectors = [row["selectorValue"] for row in rows]
    if len(selectors) != len(set(selectors)):
        raise ContractError("static initializer repeats an enum selector")
    return rows


def _fixed_ifix_signatures(path: Path) -> tuple[list[str], dict[str, Any]]:
    if not path.is_file():
        return [], {"status": "missing", "sourceLabel": repo_path(path)}
    payload = json.loads(path.read_text(encoding="utf-8"))
    signatures = sorted(
        str(row.get("signature") or "")
        for row in payload.get("fixedMethods") or []
        if isinstance(row, dict) and row.get("signature")
    )
    source = payload.get("source") or {}
    return signatures, {
        "status": "audited",
        "sourceLabel": (
            source.get("label")
            or source.get("source")
            or source.get("file")
            or repo_path(path)
        ),
        "sha256": source.get("patchSha256") or source.get("sha256") or "",
        "reportFile": repo_path(path),
        "fixedMethodCount": len(signatures),
    }


def recover_static_port_family_contract(
    spec: StaticPortFamilySpec,
    *,
    game_assembly_path: Path = DEFAULT_GAME_ASSEMBLY,
    metadata_path: Path = DEFAULT_METADATA,
    ifix_audit_path: Path = DEFAULT_IFIX_AUDIT,
) -> dict[str, Any]:
    """Recover and fail-closed validate one installed multi-output family."""
    cache_key = (
        spec,
        str(game_assembly_path.resolve()),
        str(metadata_path.resolve()),
        str(ifix_audit_path.resolve()),
    )
    if cache_key in _CONTRACT_CACHE:
        return _CONTRACT_CACHE[cache_key]
    for path in (game_assembly_path, metadata_path):
        if not path.is_file():
            raise ContractError(f"missing original input: {path}")

    catalog = _load_module("dialog_tree_control_catalog", CATALOG_PATH)
    mapper = _load_module("dialog_tree_control_mapper", MAPPER_PATH)
    metadata = catalog.Metadata(metadata_path)
    pe = mapper.PeImage(game_assembly_path)
    code_registration = mapper.DEFAULT_CODE_REGISTRATION
    metadata_registration = (
        mapper.find_metadata_registration(pe, code_registration)
        or mapper.DEFAULT_METADATA_REGISTRATION
    )
    modules = mapper.parse_codegen_modules(pe, code_registration)
    ranges = mapper.image_method_ranges(metadata)
    pointers_by_image, method_by_pointer = mapper.build_pointer_indexes(
        pe, metadata, modules, ranges
    )
    generic_index = mapper.build_generic_method_index(
        pe, metadata, code_registration, metadata_registration
    )
    for pointer, rows in generic_index.items():
        method_by_pointer.setdefault(pointer, []).extend(rows)
    all_pointers = sorted(method_by_pointer)

    def one_method(type_name: str, method_name: str, parameter_count: int | None = None) -> Any:
        matches = _method_rows(metadata, type_name, method_name)
        if parameter_count is not None:
            matches = [m for m in matches if m.parameter_count == parameter_count]
        if len(matches) != 1:
            raise ContractError(
                f"expected one {type_name}.{method_name}/{parameter_count}, found {len(matches)}"
            )
        return matches[0]

    def pointer_record(method: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        pointer, pointer_source = _method_pointer(
            method,
            metadata=metadata,
            mapper=mapper,
            ranges=ranges,
            pointers_by_image=pointers_by_image,
            generic_index=generic_index,
        )
        next_pointer = next((value for value in all_pointers if value > pointer), pointer + 0x1000)
        size = min(max(next_pointer - pointer, 1), MAX_METHOD_BYTES)
        instructions = mapper.decode_x64_subset(
            pe.bytes_at_va(pointer, size), pointer, stop_offset=size
        )
        return _method_record(metadata, method, pointer, pointer_source), instructions

    type_matches = [
        type_def
        for type_def in metadata.types
        if metadata.type_full_name(type_def) == spec.node_type
    ]
    if len(type_matches) != 1:
        raise ContractError(f"expected one node type {spec.node_type}, found {len(type_matches)}")
    node_type = type_matches[0]
    field_matches = [
        field
        for field in metadata.fields_for(node_type)
        if metadata.string(field.name_index) == spec.static_port_map_field
    ]
    if len(field_matches) != 1:
        raise ContractError(
            f"expected one {spec.node_type}.{spec.static_port_map_field}, found {len(field_matches)}"
        )
    port_field = field_matches[0]
    port_field_type = _metadata_runtime_type_name(
        pe,
        metadata,
        mapper,
        metadata_registration,
        port_field.type_index,
    )
    expected_type_fragments = (
        "System.Collections.Generic.Dictionary",
        spec.selector_enum_type,
        "System.Collections.Generic.List",
        "System.String",
    )
    if not all(fragment in port_field_type for fragment in expected_type_fragments):
        raise ContractError(
            f"static port field type mismatch: expected {expected_type_fragments}, actual {port_field_type}"
        )

    cctor = one_method(spec.node_type, ".cctor", 0)
    cctor_record, cctor_instructions = pointer_record(cctor)
    dictionary_add_targets = {
        pointer
        for pointer, rows in method_by_pointer.items()
        if any(
            str(row.get("type") or "").startswith("System.Collections.Generic.Dictionary")
            and row.get("method") == "Add"
            for row in rows
        )
    }
    initializer_rows = parse_static_enum_string_list_initializer(
        cctor_instructions,
        dictionary_add_targets=dictionary_add_targets,
        decode_literal_slot=lambda slot: _decode_string_literal_handle(
            pe, metadata, slot
        ),
    )
    enum_rows = _enum_members(metadata, spec.selector_enum_type)
    enum_by_value = {int(row["value"]): row for row in enum_rows}
    for row in initializer_rows:
        enum_row = enum_by_value.get(int(row["selectorValue"]))
        if enum_row is None:
            raise ContractError(
                f"static port selector {row['selectorValue']} is absent from {spec.selector_enum_type}"
            )
        row["selectorName"] = enum_row["name"]

    method_specs = (
        ("nodeAction", spec.node_type, spec.node_action_method, 0),
        ("managerAction", spec.manager_type, spec.manager_action_method, 1),
        ("globalAction", spec.global_action_type, spec.global_action_method, 1),
        ("managerNext", spec.manager_type, spec.manager_next_method, 1),
        ("controllerNext", spec.controller_type, spec.controller_next_method, 1),
    )
    native_methods: dict[str, dict[str, Any]] = {}
    decoded_methods: dict[str, list[dict[str, Any]]] = {}
    for key, type_name, method_name, parameter_count in method_specs:
        record, instructions = pointer_record(
            one_method(type_name, method_name, parameter_count)
        )
        native_methods[key] = record
        decoded_methods[key] = instructions

    def address(key: str) -> int:
        return int(native_methods[key]["address"], 16)

    validations = [
        {
            "gate": "node_action_calls_manager_action",
            "expected": native_methods["managerAction"]["address"],
            "actual": [f"0x{x:x}" for x in _call_targets(decoded_methods["nodeAction"])],
            "passed": address("managerAction") in _call_targets(decoded_methods["nodeAction"]),
        },
        {
            "gate": "manager_action_calls_global_action",
            "expected": native_methods["globalAction"]["address"],
            "actual": [f"0x{x:x}" for x in _call_targets(decoded_methods["managerAction"])],
            "passed": address("globalAction") in _call_targets(decoded_methods["managerAction"]),
        },
        {
            "gate": "controller_accepts_explicit_nonnegative_index",
            "expected": "signed-negative test before continuation",
            "actual": [row.get("text") for row in decoded_methods["controllerNext"]],
            "passed": any(
                str(row.get("text") or "").startswith("jns 0x")
                for row in decoded_methods["controllerNext"]
            ),
        },
    ]
    failed = [row for row in validations if not row["passed"]]
    if failed:
        first = failed[0]
        raise ContractError(
            "validator=dialog_tree_static_port_contract "
            f"gate={first['gate']} expected={first['expected']!r} actual={first['actual']!r}"
        )

    ifix_signatures, ifix_source = _fixed_ifix_signatures(ifix_audit_path)
    relevant_prefixes = {
        f"{type_name}::{method_name}("
        for _key, type_name, method_name, _parameter_count in method_specs
    }
    relevant_ifix = [
        signature
        for signature in ifix_signatures
        if any(signature.startswith(prefix) for prefix in relevant_prefixes)
    ]
    if relevant_ifix:
        raise ContractError(
            "validator=dialog_tree_static_port_contract gate=current_ifix_exclusion "
            f"expected=[] actual={relevant_ifix!r} source={ifix_audit_path}"
        )

    game_hash = sha256_file(game_assembly_path)
    metadata_hash = sha256_file(metadata_path)
    contract = {
        "schema": "dialogTreeStaticPortFamilyContract.v1",
        "status": "validated",
        "family": spec.family,
        "nodeType": spec.node_type,
        "selectorEnumType": spec.selector_enum_type,
        "serializedSelectorPath": list(spec.serialized_selector_path),
        "staticPortMapField": {
            "name": spec.static_port_map_field,
            "token": f"0x{port_field.token:08x}",
            "type": port_field_type,
        },
        "enumMembers": enum_rows,
        "portMaps": [
            {
                "selectorValue": row["selectorValue"],
                "selectorName": row["selectorName"],
                "labels": [literal["value"] for literal in row["labels"]],
                "literalEvidence": row["labels"],
                "dictionaryAddCallVa": row["dictionaryAddCallVa"],
            }
            for row in initializer_rows
        ],
        "nativeMethods": native_methods,
        "staticInitializer": cctor_record,
        "validation": {
            "validator": "dialog_tree_static_port_contract",
            "status": "validated",
            "checks": validations,
            "sourceFiles": [str(game_assembly_path.resolve()), str(metadata_path.resolve())],
            "sourceHashes": {
                "GameAssembly.dll": game_hash,
                "global-metadata.dat": metadata_hash,
            },
        },
        "currentIFix": {
            **ifix_source,
            "relevantFixedMethods": relevant_ifix,
        },
        "selectionRule": (
            "A nonnegative DialogManager.Next(index) reaches DialogTreeController.Next(index), "
            "which uses that explicit serialized outgoing ordinal. Negative indexes use the "
            "node's GetNextIndex fallback. Named static port-list order labels the matching "
            "serialized outgoing ordinal; the UI result occurrence itself remains external."
        ),
        "evidenceBoundary": (
            "This recovers authored multi-output alternatives and exact names where the "
            "installed static port map supplies them. It does not observe which UI result "
            "occurred, assign mission ownership, or prove cross-file chronology."
        ),
        "sources": {
            "gameAssembly": str(game_assembly_path.resolve()),
            "gameAssemblySha256": game_hash,
            "globalMetadata": str(metadata_path.resolve()),
            "globalMetadataSha256": metadata_hash,
        },
    }
    _CONTRACT_CACHE[cache_key] = contract
    return contract


def selector_value(node: dict[str, Any], path: Iterable[str]) -> tuple[int, bool]:
    value: Any = node
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return 0, True
        value = value[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"serialized selector is not an integer: {value!r}")
    return value, False


def project_serialized_family_node(
    node: dict[str, Any],
    outgoing: list[tuple[int, str]],
    *,
    target_types: dict[str, str],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Project one serialized node through a recovered native family contract."""
    selector, defaulted = selector_value(
        node, contract.get("serializedSelectorPath") or []
    )
    enum_by_value = {
        int(row["value"]): str(row["name"])
        for row in contract.get("enumMembers") or []
    }
    if selector not in enum_by_value:
        raise ContractError(f"selector {selector} is absent from installed enum")
    port_map = next(
        (
            row
            for row in contract.get("portMaps") or []
            if int(row.get("selectorValue", -1)) == selector
        ),
        None,
    )
    labels = list((port_map or {}).get("labels") or [])
    if labels and len(labels) != len(outgoing):
        raise ContractError(
            "validator=dialog_tree_serialized_multi_output "
            "gate=named_port_count_matches_outgoing "
            f"expected={len(labels)} actual={len(outgoing)} selector={selector}"
        )
    arms = []
    for ordinal, (connection_index, target_id) in enumerate(outgoing):
        arms.append({
            "connectionOrdinal": ordinal,
            "connectionIndex": connection_index,
            "outcomeLabel": labels[ordinal] if ordinal < len(labels) else "",
            "outcomeStatus": "native_named_port" if ordinal < len(labels) else "external_index_unlabeled",
            "targetNodeId": target_id,
            "targetNodeType": target_types.get(target_id, ""),
        })
    return {
        "selectorValue": selector,
        "selectorName": enum_by_value[selector],
        "selectorDefaulted": defaulted,
        "portContractStatus": "native_named_ports" if labels else "external_index_unlabeled",
        "arms": arms,
    }
