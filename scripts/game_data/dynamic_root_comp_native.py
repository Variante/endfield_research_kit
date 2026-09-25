"""Validate selected RootComp groups, template lookup, and DataIndex spans.

Native code establishes the inline layout, typed template lookup, and a
conditional consumer path. The current VFS-backed corpus establishes exact
directory partitions and ordered per-entity signatures, but does not observe
live grid activation or the runtime template list contents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_data_index_native import (
    FIELD_FORMATS,
    _payload_grids as data_index_payload_grids,
    validate_native_layout as validate_data_index_layout,
)
from scripts.game_data.dynamic_main_native import _checked_dump_path
from scripts.game_data.dynamic_stream_area_corpus import (
    DEFAULT_CLI,
    DEFAULT_LEDGER,
    DEFAULT_OUTER,
    MAIN_NAME_RE,
    load_current_inputs,
)
from scripts.game_data.dynamic_streaming import _bounded_vector, _field_span, _root_layout, _table_layout
from scripts.game_data.dynamic_system_routing_native import (
    CONTRACT as ROUTE_CONTRACT,
    SCHEMA as ROUTE_SCHEMA,
    validate_native_routes,
)
from scripts.game_data.extraction.verify_export_freshness import DEFAULT_SUMMARY, build_report as export_freshness_report
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context import generic_type_carrier, literal_record, unresolved_usage_index
from scripts.game_data.il2cpp.protocol import (
    field_defaults, native_enum_members, read_compressed_int32, runtime_type_field_offsets,
)
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_root_comp_native.json"
SCHEMA = "endfield.dynamic-root-comp-native-contract.v7"
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_root_comp_native_latest.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports/animestudio/dynamic_root_comp_native_latest.md"


class DynamicRootCompError(ValueError):
    """The selected layout, consumer, or authored grid partition differs."""


def _unique(raw: bytes, pattern: bytes, label: str) -> int:
    position = raw.find(pattern)
    if position < 0 or raw.find(pattern, position + 1) >= 0:
        raise DynamicRootCompError(f"{label}: native instruction pattern differs")
    return position


def _byte_after(raw: bytes, prefix: bytes, label: str) -> int:
    position = _unique(raw, prefix, label)
    if position + len(prefix) >= len(raw):
        raise DynamicRootCompError(f"{label}: native instruction is truncated")
    return raw[position + len(prefix)]


def _call_target(raw: bytes, offset: int, method_rva: int, label: str) -> int:
    if offset < 0 or offset + 5 > len(raw) or raw[offset] != 0xE8:
        raise DynamicRootCompError(f"{label}: selected relative call differs")
    return method_rva + offset + 5 + struct.unpack_from("<i", raw, offset + 1)[0]


def _instruction(raw: bytes, offset: int, prefix: bytes, label: str) -> int:
    if offset < 0 or offset + len(prefix) + 1 > len(raw) or raw[offset:offset + len(prefix)] != prefix:
        raise DynamicRootCompError(f"{label}: selected instruction differs")
    return raw[offset + len(prefix)]


def _mov_edx_imm32(raw: bytes, offset: int, label: str) -> int:
    if offset < 0 or offset + 5 > len(raw) or raw[offset] != 0xBA:
        raise DynamicRootCompError(f"{label}: selected mov edx, immediate differs")
    return struct.unpack_from("<I", raw, offset + 1)[0]


def _mov_eax_imm32(raw: bytes, offset: int, label: str) -> int:
    if offset < 0 or offset + 5 > len(raw) or raw[offset] != 0xB8:
        raise DynamicRootCompError(f"{label}: selected mov eax, immediate differs")
    return struct.unpack_from("<I", raw, offset + 1)[0]


def _field_type(image: Any, type_index: int, field_name: str, field_type_index: int, offset: int) -> bytes:
    """Check a selected runtime field, then return its registered type record."""
    owner = image.metadata.types[type_index]
    fields = {image.metadata.string(row.name_index): row for row in image.metadata.fields_for(owner)}
    field = fields.get(field_name)
    offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, type_index)
    if field is None or field.type_index != field_type_index or offsets.get(field_name) != offset:
        raise DynamicRootCompError(f"{image.type_name(type_index)}.{field_name} type/offset differs")
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + field.type_index * 8)
    return image.pe.bytes_at_va(pointer, 16)


def _class_type_definition(image: Any, type_index: int, label: str) -> int:
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + type_index * 8)
    raw = image.pe.bytes_at_va(pointer, 16)
    if raw[10] != 0x12:
        raise DynamicRootCompError(f"{label} is not a registered class type")
    definition = struct.unpack_from("<I", raw)[0]
    if definition >= len(image.metadata.types):
        raise DynamicRootCompError(f"{label} class definition index exceeds metadata")
    return definition


def _validate_visibility_code(
    selected: dict[str, Any], *, register_entity: bytes, register_entity_rva: int,
    controller_register: bytes, controller_register_rva: int,
    state_getter: bytes, area_getter: bytes, primitive_helper: bytes,
    root_slot: int, root_width: int, visible_offset: int, area_offset: int,
    primitive_slot: int, group_num_rva: int, index_getter_rva: int,
) -> None:
    """Check the selected path from RootComp.VisibleDesc to primitive integers."""
    for name, field in (("Area", "area"), ("State", "state")):
        offset = int(selected[f"registerEntity{name}FieldReadOffset"])
        field_offset = int(selected[f"{field}ControllerFieldOffset"])
        if register_entity[offset:offset + 7] != b"\x48\x8b\x8f" + struct.pack("<I", field_offset):
            raise DynamicRootCompError(f"RegisterEntity {field} controller field read differs")
        grid_pass = int(selected[f"registerEntity{name}GridPassOffset"])
        if register_entity[grid_pass:grid_pass + 3] != b"\x4d\x8b\xce":
            raise DynamicRootCompError(f"RegisterEntity {field} grid argument differs")
        if _call_target(
            register_entity, int(selected[f"registerEntity{name}CallOffset"]),
            register_entity_rva, f"RegisterEntity {field} controller Register",
        ) != controller_register_rva:
            raise DynamicRootCompError(f"RegisterEntity {field} controller call differs")
    for name, getter in (("state", state_getter), ("area", area_getter)):
        if _mov_edx_imm32(getter, int(selected["getterRootSlotOffset"]), name + " RootComp slot") != root_slot:
            raise DynamicRootCompError(f"{name} visibility controller RootComp slot differs")
        if _instruction(getter, int(selected["getterRootStrideOffset"]), b"\x6b\xc6",
                        name + " RootComp stride") != root_width:
            raise DynamicRootCompError(f"{name} visibility controller RootComp stride differs")
        if _instruction(getter, int(selected["getterVisibleDescOffset"]), b"\x83\xc2",
                        name + " VisibleDesc offset") != visible_offset:
            raise DynamicRootCompError(f"{name} visibility controller VisibleDesc offset differs")
    state_read = int(selected["stateGetterGroupReadOffset"])
    state_call = int(selected["stateGetterGroupCallOffset"])
    if (state_getter[state_read:state_read + 4] != b"\x66\x0f\x7e\xd2"
            or state_getter[state_call:state_call + 1] != b"\xe8"
            or b"\x83\xc2" in state_getter[state_read + 4:state_call]):
        raise DynamicRootCompError("state visibility controller group offset differs")
    if _instruction(area_getter, int(selected["areaGetterGroupOffset"]), b"\x83\xc2",
                    "area group offset") != area_offset:
        raise DynamicRootCompError("area visibility controller group offset differs")
    vcall_load = int(selected["registerVirtualGroupLoadOffset"])
    vcall = int(selected["registerVirtualGroupCallOffset"])
    if (controller_register[vcall_load:vcall_load + 7] != b"\x4c\x8b\x90\x90\x01\x00\x00"
            or controller_register[vcall:vcall + 3] != b"\x41\xff\xd2"):
        raise DynamicRootCompError("visibility Register virtual group lookup differs")
    if _call_target(controller_register, int(selected["registerNumCallOffset"]),
                    controller_register_rva, "visibility group Num") != group_num_rva:
        raise DynamicRootCompError("visibility Register group Num getter differs")
    positive = int(selected["registerNumPositiveTestOffset"])
    if controller_register[positive:positive + 4] != b"\x85\xc0\x0f\x8e":
        raise DynamicRootCompError("visibility Register group Num positive guard differs")
    if _call_target(controller_register, int(selected["registerIndexCallOffset"]),
                    controller_register_rva, "visibility DataIndex.Index") != index_getter_rva:
        raise DynamicRootCompError("visibility Register DataIndex.Index getter differs")
    if controller_register[int(selected["registerPrimitiveReadArgumentOffset"]):
                           int(selected["registerPrimitiveReadArgumentOffset"]) + 4] != b"\x42\x8d\x14\x2e":
        raise DynamicRootCompError("visibility Register Index plus loop position differs")
    if _call_target(controller_register, int(selected["registerPrimitiveReadCallOffset"]),
                    controller_register_rva, "visibility PrimitiveIntList reader") != int(selected["primitiveHelperRva"]):
        raise DynamicRootCompError("visibility Register PrimitiveIntList reader differs")
    if (_mov_edx_imm32(primitive_helper, int(selected["primitiveHelperSlotOffset"]),
                       "visibility primitive vector slot") != primitive_slot
            or primitive_helper[int(selected["primitiveHelperStrideOffset"]):
                                int(selected["primitiveHelperStrideOffset"]) + 3] != b"\x8d\x3c\xbb"
            or primitive_helper[int(selected["primitiveHelperValueReadOffset"]):
                                int(selected["primitiveHelperValueReadOffset"]) + 2] != b"\x8b\x1e"):
        raise DynamicRootCompError("visibility primitive vector slot/stride/read differs")


def _generic_field(image: Any, type_index: int, field_name: str, field_type_index: int,
                   offset: int, base_name: str, arguments: list[str]) -> None:
    raw = _field_type(image, type_index, field_name, field_type_index, offset)
    if raw[10] != 0x15:
        raise DynamicRootCompError(f"{field_name} is not a registered generic type")
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + field_type_index * 8)
    carrier_pointer = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(carrier_pointer, 32)
    base_pointer = struct.unpack_from("<Q", carrier_raw)[0]
    carrier = generic_type_carrier(
        raw, carrier_raw, image.pe.bytes_at_va(base_pointer, 16),
        type_pointer=pointer, type_count=len(image.metadata.types), source=str(image.gameassembly),
    )
    inst = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    found = []
    for argument in inst.arguments:
        arg = bytes.fromhex(argument.raw_type_record_hex)
        if arg[10] not in (0x11, 0x12):
            raise DynamicRootCompError(f"{field_name} generic argument has an unreviewed type tag")
        found.append(image.type_name(struct.unpack_from("<I", arg)[0]))
    if image.type_name(carrier["baseDefinitionIndex"]) != base_name or found != arguments:
        raise DynamicRootCompError(f"{field_name} generic type differs: {found}")


def _method_spec_usage(image: Any, raw: bytes, method_rva: int, offset: int,
                       prefix: bytes, selected_index: int, label: str) -> tuple[int, str, str, list[str], list[str]]:
    """Resolve one selected tag-six call-site method spec and its type arguments."""
    if raw[offset:offset + 3] != prefix:
        raise DynamicRootCompError(f"{label} method usage load differs")
    usage_va = image.pe.image_base + method_rva + offset + 7 + struct.unpack_from("<i", raw, offset + 3)[0]
    spec_index = unresolved_usage_index(
        image.pe.bytes_at_va(usage_va, 8), image.registration["methodSpecsCount"],
        tag=6, source=str(image.gameassembly), offset=usage_va,
    )
    if spec_index != selected_index:
        raise DynamicRootCompError(f"{label} method spec differs")
    spec_va = int(image.registration["methodSpecs"], 16) + spec_index * 12
    method_index, class_inst, method_inst = struct.unpack("<iii", image.pe.bytes_at_va(spec_va, 12))
    method = image.metadata.methods[method_index]

    def names(inst_index: int) -> list[str]:
        if inst_index < 0:
            return []
        result = []
        for argument in image.instantiations.resolve(inst_index).arguments:
            arg = bytes.fromhex(argument.raw_type_record_hex)
            if arg[10] not in (0x11, 0x12):
                raise DynamicRootCompError(f"{label} method spec has an unreviewed type tag")
            result.append(image.type_name(struct.unpack_from("<I", arg)[0]))
        return result

    return (method_index, image.type_name(method.declaring_type), image.metadata.string(method.name_index),
            names(class_inst), names(method_inst))


def _template_path_literal(image: Any, raw: bytes, method_rva: int,
                           selected: dict[str, Any]) -> str:
    """Join OnInit's literal usage to its declared TEMPLATE_PATH default."""
    fields = {image.metadata.string(row.name_index): row
              for row in image.metadata.fields_for(image.metadata.types[int(selected["systemTypeIndex"])])}
    path_field = fields.get(selected["templatePathField"])
    if path_field is None or path_field.index != int(selected["templatePathFieldIndex"]):
        raise DynamicRootCompError("TEMPLATE_PATH field identity differs")
    default = field_defaults(image.metadata).get(path_field.index)
    if default is None:
        raise DynamicRootCompError("TEMPLATE_PATH has no selected metadata default")
    section = image.metadata.sections["fieldAndParameterDefaultValueData"]
    at = section.offset + default[1]
    length, prefix_width = read_compressed_int32(image.metadata.buf, at)
    if length < 0 or at + prefix_width + length > section.offset + section.size:
        raise DynamicRootCompError("TEMPLATE_PATH default exceeds selected metadata blob")
    declared = image.metadata.buf[at + prefix_width:at + prefix_width + length].decode("utf-8")
    offset = int(selected["onInitPathLiteralLoadOffset"])
    if raw[offset:offset + 3] != b"\x48\x8b\x0d":
        raise DynamicRootCompError("OnInit template path literal load differs")
    usage_va = image.pe.image_base + method_rva + offset + 7 + struct.unpack_from("<i", raw, offset + 3)[0]
    row_start, row_size, pool_start, pool_size = struct.unpack_from("<iiii", image.metadata.buf, 8)
    if (row_start < 24 or row_size < 0 or row_size % 8 or row_start + row_size > len(image.metadata.buf)
            or pool_start < row_start + row_size or pool_size < 0
            or pool_start + pool_size > len(image.metadata.buf)):
        raise DynamicRootCompError("selected string-literal table bounds differ")
    literal_index = unresolved_usage_index(
        image.pe.bytes_at_va(usage_va, 8), row_size // 8,
        tag=5, source=str(image.gameassembly), offset=usage_va,
    )
    if literal_index != int(selected["onInitPathLiteralIndex"]):
        raise DynamicRootCompError("OnInit template path literal index differs")
    row_at = row_start + literal_index * 8
    start, size = literal_record(
        image.metadata.buf[row_at:row_at + 8], pool_size,
        source=str(image.metadata_path), offset=row_at,
    )
    literal = image.metadata.buf[pool_start + start:pool_start + start + size].decode("utf-8")
    if declared != literal or literal != selected["templateAssetPath"]:
        raise DynamicRootCompError("TEMPLATE_PATH default and OnInit literal differ")
    return literal


def _validate_id_comp_control_flow(raw: bytes, selected: dict[str, Any]) -> None:
    """Check the selected IdComp detour and its return to the shared route."""
    type_id = int(selected["dataTypeValue"])
    saved = int(selected["typeSavedOffset"])
    comparison = int(selected["typeCompareOffset"])
    if raw[saved:saved + 2] != b"\x8b\xd8" or raw[comparison:comparison + 3] != bytes((0x83, 0xF8, type_id)):
        raise DynamicRootCompError("_ParseLoad DataIndex.Type to IdComp comparison differs")
    branch = int(selected["specialBranchOffset"])
    if raw[branch:branch + 2] != b"\x0f\x84" or branch + 6 + struct.unpack_from("<i", raw, branch + 2)[0] != int(selected["specialTargetOffset"]):
        raise DynamicRootCompError("_ParseLoad IdComp special branch differs")
    jump = int(selected["returnJumpOffset"])
    if raw[jump] != 0xE9 or jump + 5 + struct.unpack_from("<i", raw, jump + 1)[0] != int(selected["routeRejoinOffset"]):
        raise DynamicRootCompError("IdComp detour does not rejoin common route")
    if raw[int(selected["routeArgumentOffset"]):int(selected["routeArgumentOffset"]) + 2] != b"\x8b\xd3":
        raise DynamicRootCompError("common route does not receive DataIndex.Type")


def _validate_template_lookup(image: Any, layout: dict[str, Any], methods: dict[int, dict[str, Any]],
                              raw_methods: dict[int, bytes]) -> None:
    """Prove the typed template map and the source of the inner loop bound."""
    selected = layout["templateLookup"]
    system_index = int(selected["systemTypeIndex"])
    template_index = int(selected["templateTypeIndex"])
    if image.type_name(system_index) != methods[int(layout["parseLoadMethodIndex"])]["type"]:
        raise DynamicRootCompError("template map owner differs from _ParseLoad owner")
    if image.type_name(template_index) != selected["mapArguments"][1]:
        raise DynamicRootCompError("template data type differs from dictionary value")
    _generic_field(
        image, system_index, selected["mapField"], int(selected["mapFieldTypeIndex"]),
        int(selected["mapFieldOffset"]), selected["mapType"], selected["mapArguments"],
    )
    entity_raw = _field_type(
        image, template_index, selected["entityTypeField"],
        int(selected["entityTypeFieldTypeIndex"]), int(selected["entityTypeFieldOffset"]),
    )
    if entity_raw[10] not in (0x11, 0x12) or image.type_name(struct.unpack_from("<I", entity_raw)[0]) != layout["entityEnumType"]:
        raise DynamicRootCompError("template entityType registered type differs")
    _generic_field(
        image, template_index, selected["compsField"], int(selected["compsFieldTypeIndex"]),
        int(selected["compsFieldOffset"]), selected["compsType"], selected["compsArguments"],
    )
    asset_index = int(selected["templateAssetTypeIndex"])
    if image.type_name(asset_index) != selected["templateAssetType"]:
        raise DynamicRootCompError("DynamicSceneTemplates asset type differs")
    _generic_field(
        image, asset_index, selected["templateListField"], int(selected["templateListFieldTypeIndex"]),
        int(selected["templateListFieldOffset"]), selected["templateListType"],
        [selected["mapArguments"][1]],
    )
    parse = methods[int(layout["parseLoadMethodIndex"])]
    raw = raw_methods[parse["index"]]
    map_offset = int(selected["mapFieldOffset"])
    if raw[int(selected["parseMapReadOffset"]):int(selected["parseMapReadOffset"]) + 4] != bytes((0x49, 0x8B, 0x4F, map_offset)):
        raise DynamicRootCompError("_ParseLoad template map field read differs")
    if raw[int(selected["parseKeyReadOffset"]):int(selected["parseKeyReadOffset"]) + 4] != b"\x40\x0f\xb6\xd6":
        raise DynamicRootCompError("_ParseLoad RootComp.Type dictionary key differs")
    if raw[int(selected["parseLookupOutOffset"]):int(selected["parseLookupOutOffset"]) + 4] != b"\x4c\x8d\x45\xd8":
        raise DynamicRootCompError("_ParseLoad template lookup out slot differs")
    if _call_target(raw, int(selected["parseLookupCallOffset"]), int(parse["rva"]), "template TryGetValue") != int(selected["tryGetValueTargetRva"]):
        raise DynamicRootCompError("_ParseLoad template TryGetValue target differs")
    if raw[int(selected["parseLookupValueReadOffset"]):int(selected["parseLookupValueReadOffset"]) + 4] != b"\x48\x8b\x4d\xd8":
        raise DynamicRootCompError("_ParseLoad looked-up template value read differs")
    if raw[int(selected["parseCompsReadOffset"]):int(selected["parseCompsReadOffset"]) + 4] != bytes((0x48, 0x8B, 0x49, int(selected["compsFieldOffset"]))):
        raise DynamicRootCompError("_ParseLoad template comps field read differs")
    if _call_target(raw, int(layout["consumer"]["innerCountCallOffset"]), int(parse["rva"]), "template SafeCount") != int(selected["safeCountTargetRva"]):
        raise DynamicRootCompError("_ParseLoad template SafeCount target differs")
    if _method_spec_usage(
        image, raw, int(parse["rva"]), int(selected["safeCountUsageLoadOffset"]),
        b"\x48\x8b\x15", int(selected["safeCountMethodSpecIndex"]), "_ParseLoad SafeCount",
    ) != (int(selected["safeCountMethodIndex"]), "Beyond.CollectionExtensions", "SafeCount", [], selected["compsArguments"]):
        raise DynamicRootCompError("_ParseLoad SafeCount instantiation differs from template comps")
    on_init = methods[int(selected["onInitMethodIndex"])]
    init_raw = raw_methods[on_init["index"]]
    if on_init["parameters"] or on_init["returnType"] != "System.Void":
        raise DynamicRootCompError("OnInit signature differs")
    _template_path_literal(image, init_raw, int(on_init["rva"]), selected)
    source_calls = (
        ("onInitPathHelperCallOffset", "onInitPathHelperTargetRva", "template path helper"),
        ("onInitTryLoadCallOffset", "onInitTryLoadTargetRva", "TryLoad<DynamicSceneTemplates>"),
        ("onInitGetCallOffset", "onInitGetTargetRva", "Get<DynamicSceneTemplates>"),
        ("onInitSafeCountCallOffset", "onInitSafeCountTargetRva", "SafeCount<DynamicSceneEntityTemplateData>"),
        ("onInitItemCallOffset", "onInitItemTargetRva", "List<DynamicSceneEntityTemplateData>.get_Item"),
    )
    for offset_key, target_key, label in source_calls:
        if _call_target(init_raw, int(selected[offset_key]), int(on_init["rva"]), label) != int(selected[target_key]):
            raise DynamicRootCompError(f"OnInit {label} call target differs")
    if init_raw[int(selected["onInitPathResultSaveOffset"]):int(selected["onInitPathResultSaveOffset"]) + 3] != b"\x48\x8b\xd8":
        raise DynamicRootCompError("OnInit path helper result storage differs")
    if init_raw[int(selected["onInitTryLoadPathPassOffset"]):int(selected["onInitTryLoadPathPassOffset"]) + 3] != b"\x48\x8b\xcb":
        raise DynamicRootCompError("OnInit resource load path argument differs")
    if _method_spec_usage(
        image, init_raw, int(on_init["rva"]), int(selected["onInitTryLoadUsageOffset"]),
        b"\x48\x8b\x05", int(selected["onInitTryLoadMethodSpecIndex"]), "OnInit TryLoad",
    ) != (int(selected["onInitTryLoadMethodIndex"]), "Beyond.Resource.ResourceManager", "TryLoad", [], [selected["templateAssetType"]]):
        raise DynamicRootCompError("OnInit TryLoad template instantiation differs")
    if _method_spec_usage(
        image, init_raw, int(on_init["rva"]), int(selected["onInitGetUsageOffset"]),
        b"\x48\x8b\x15", int(selected["onInitGetMethodSpecIndex"]), "OnInit Get",
    ) != (int(selected["onInitGetMethodIndex"]), "Beyond.Resource.FAssetProxyHandle", "Get", [], [selected["templateAssetType"]]):
        raise DynamicRootCompError("OnInit asset handle Get instantiation differs")
    list_offset = int(selected["templateListFieldOffset"])
    if init_raw[int(selected["onInitListCountReadOffset"]):int(selected["onInitListCountReadOffset"]) + 4] != bytes((0x48, 0x8B, 0x48, list_offset)):
        raise DynamicRootCompError("OnInit templateDataList count source differs")
    if init_raw[int(selected["onInitListItemReadOffset"]):int(selected["onInitListItemReadOffset"]) + 4] != bytes((0x48, 0x8B, 0x4F, list_offset)):
        raise DynamicRootCompError("OnInit templateDataList item source differs")
    if _method_spec_usage(
        image, init_raw, int(on_init["rva"]), int(selected["onInitSafeCountUsageOffset"]),
        b"\x48\x8b\x15", int(selected["onInitSafeCountMethodSpecIndex"]), "OnInit SafeCount",
    ) != (int(selected["onInitSafeCountMethodIndex"]), "Beyond.CollectionExtensions", "SafeCount", [], [selected["mapArguments"][1]]):
        raise DynamicRootCompError("OnInit templateDataList SafeCount instantiation differs")
    if _method_spec_usage(
        image, init_raw, int(on_init["rva"]), int(selected["onInitItemUsageOffset"]),
        b"\x4c\x8b\x05", int(selected["onInitItemMethodSpecIndex"]), "OnInit get_Item",
    ) != (int(selected["onInitItemMethodIndex"]), selected["templateListType"], "get_Item", [selected["mapArguments"][1]], []):
        raise DynamicRootCompError("OnInit templateDataList item instantiation differs")
    if init_raw[int(selected["onInitMapReadOffset"]):int(selected["onInitMapReadOffset"]) + 4] != bytes((0x48, 0x8B, 0x4E, map_offset)):
        raise DynamicRootCompError("OnInit template map field read differs")
    if init_raw[int(selected["onInitValuePassOffset"]):int(selected["onInitValuePassOffset"]) + 3] != b"\x4c\x8b\xc0":
        raise DynamicRootCompError("OnInit template value argument differs")
    if init_raw[int(selected["onInitKeyReadOffset"]):int(selected["onInitKeyReadOffset"]) + 4] != bytes((0x0F, 0xB6, 0x50, int(selected["entityTypeFieldOffset"]))):
        raise DynamicRootCompError("OnInit template entityType key read differs")
    if _call_target(init_raw, int(selected["onInitAddCallOffset"]), int(on_init["rva"]), "template Add") != int(selected["addTargetRva"]):
        raise DynamicRootCompError("OnInit template Add target differs")
    generic = image.mapper.build_generic_method_index(
        image.pe, image.metadata, image.code_registration, image.metadata_registration,
    )
    for target_key, index_key, name in (
        ("tryGetValueTargetRva", "tryGetValueMethodIndex", "TryGetValue"),
        ("addTargetRva", "addMethodIndex", "Add"),
    ):
        rows = generic.get(image.pe.image_base + int(selected[target_key]), [])
        matches = [row for row in rows if row["methodIndex"] == int(selected[index_key])
                   and row["type"] == selected["mapType"] and row["method"] == name
                   and [arg["typeName"] for arg in row["classInstantiation"]["arguments"]] == selected["genericSharedArguments"]]
        if len(rows) != 1 or len(matches) != 1:
            raise DynamicRootCompError(f"template Dictionary.{name} generic target differs")
    for target_key, index_key, owner, name in (
        ("onInitTryLoadTargetRva", "onInitTryLoadMethodIndex", "Beyond.Resource.ResourceManager", "TryLoad"),
        ("onInitGetTargetRva", "onInitGetMethodIndex", "Beyond.Resource.FAssetProxyHandle", "Get"),
        ("onInitItemTargetRva", "onInitItemMethodIndex", selected["templateListType"], "get_Item"),
    ):
        rows = generic.get(image.pe.image_base + int(selected[target_key]), [])
        if len(rows) != 1 or (rows[0]["methodIndex"], rows[0]["type"], rows[0]["method"]) != (int(selected[index_key]), owner, name):
            raise DynamicRootCompError(f"OnInit {owner}.{name} generic target differs")


def _validate_id_comp_path(
    image: Any, layout: dict[str, Any], main_layout: dict[str, Any],
    index_layout: dict[str, Any], enum_by_id: dict[int, str],
    methods: dict[int, dict[str, Any]], raw_methods: dict[int, bytes],
) -> None:
    """Prove the selected IdComp detour and its return to the common route."""
    selected = layout["idCompPath"]
    type_id = int(selected["dataTypeValue"])
    if enum_by_id.get(type_id) != "IdComp":
        raise DynamicRootCompError("selected IdComp data type differs")
    vector = next((row for row in main_layout["vectors"]
                   if int(row["fieldIndex"]) == int(selected["vectorFieldIndex"])), None)
    if (vector is None or vector["name"] != "IdComp" or vector["elementType"] != selected["vectorType"]
            or int(vector["elementWidth"]) != 8):
        raise DynamicRootCompError("selected IdComp vector binding differs")
    getter = methods[int(selected["uniqueIdGetterMethodIndex"])]
    if (getter["type"], getter["method"], getter["parameters"], getter["returnType"]) != (
        selected["vectorType"], "get_UniqueId", [], "System.UInt64",
    ):
        raise DynamicRootCompError("IdComp.UniqueId getter identity differs")
    parse = methods[int(layout["parseLoadMethodIndex"])]
    raw = raw_methods[parse["index"]]
    _validate_id_comp_control_flow(raw, selected)
    fields = {row["name"]: row for row in index_layout["fields"]}
    index_getter = image.metadata.methods[int(fields["Index"]["getterMethodIndex"])]
    if _call_target(raw, int(selected["indexGetterCallOffset"]), int(parse["rva"]), "IdComp DataIndex.get_Index") != image.method_pointer_va(index_getter) - image.pe.image_base:
        raise DynamicRootCompError("IdComp detour does not read DataIndex.Index")
    if raw[int(selected["indexPassOffset"]):int(selected["indexPassOffset"]) + 3] != b"\x44\x8b\xc0":
        raise DynamicRootCompError("IdComp vector index argument differs")
    if raw[int(selected["gridPassOffset"]):int(selected["gridPassOffset"]) + 3] != b"\x49\x8b\xd5":
        raise DynamicRootCompError("IdComp containing grid argument differs")
    helper_rva = int(selected["helperRva"])
    if _call_target(raw, int(selected["helperCallOffset"]), int(parse["rva"]), "IdComp vector helper") != helper_rva:
        raise DynamicRootCompError("IdComp vector helper target differs")
    helper = image.pe.bytes_at_va(image.pe.image_base + helper_rva, int(selected["helperWindowLength"]))
    if hashlib.sha256(helper).hexdigest().upper() != selected["helperWindowSha256"].upper():
        raise DynamicRootCompError("IdComp native helper code window differs")
    if _mov_edx_imm32(helper, int(selected["helperVectorSlotOffset"]), "IdComp vector slot") != int(vector["vtableSlot"]):
        raise DynamicRootCompError("IdComp helper vector slot differs")
    for offset_key, target_key, label in (
        ("helperVectorSelectorCallOffset", "helperVectorSelectorTargetRva", "vector selector"),
        ("helperVectorBodyCallOffset", "helperVectorBodyTargetRva", "vector body"),
    ):
        if _call_target(helper, int(selected[offset_key]), helper_rva, label) != int(selected[target_key]):
            raise DynamicRootCompError(f"IdComp helper {label} target differs")
    if helper[int(selected["helperStrideOffset"]):int(selected["helperStrideOffset"]) + 3] != b"\x8d\x14\xf0":
        raise DynamicRootCompError("IdComp helper eight-byte stride differs")
    getter_raw = raw_methods[getter["index"]]
    scalar_reader = _call_target(
        getter_raw, int(selected["uniqueIdGetterScalarCallOffset"]), int(getter["rva"]),
        "IdComp.get_UniqueId scalar reader",
    )
    if _call_target(raw, int(selected["uniqueIdScalarCallOffset"]), int(parse["rva"]), "IdComp.UniqueId scalar reader") != scalar_reader:
        raise DynamicRootCompError("IdComp detour scalar reader differs from generated getter")


def _validate_visibility_consumer(
    image: Any, layout: dict[str, Any], main_layout: dict[str, Any],
    index_layout: dict[str, Any], methods: dict[int, dict[str, Any]],
    raw_methods: dict[int, bytes],
) -> None:
    selected = layout["visibilityConsumer"]
    register_entity = image.metadata.methods[int(layout["registerEntityMethodIndex"])]
    owner = image.metadata.types[register_entity.declaring_type]
    owner_fields = {image.metadata.string(row.name_index): row for row in image.metadata.fields_for(owner)}
    for kind in ("state", "area"):
        field_name = selected[f"{kind}ControllerField"]
        field = owner_fields.get(field_name)
        if field is None or field.index != int(selected[f"{kind}ControllerFieldIndex"]):
            raise DynamicRootCompError(f"{kind} visibility controller field identity differs")
        raw_type = _field_type(
            image, owner.index, field_name, int(selected[f"{kind}ControllerFieldTypeIndex"]),
            int(selected[f"{kind}ControllerFieldOffset"]),
        )
        if raw_type[10] != 0x12:
            raise DynamicRootCompError(f"{kind} visibility controller field is not a class")
        definition = struct.unpack_from("<I", raw_type)[0]
        if image.type_name(definition) != selected[f"{kind}ControllerType"]:
            raise DynamicRootCompError(f"{kind} visibility controller class differs")
        parent = _class_type_definition(
            image, image.metadata.types[definition].parent_index, f"{kind} visibility controller parent",
        )
        grandparent = _class_type_definition(
            image, image.metadata.types[parent].parent_index, f"{kind} visibility controller grandparent",
        )
        if (image.type_name(parent) != selected["entityControllerBaseType"]
                or image.type_name(grandparent) != selected["baseControllerType"]):
            raise DynamicRootCompError(f"{kind} visibility controller inheritance differs")
    base_register = image.metadata.methods[int(selected["baseRegisterMethodIndex"])]
    entity_params = image.metadata.parameters_for(register_entity)
    base_params = image.metadata.parameters_for(base_register)
    if (len(entity_params) != 5 or len(base_params) != 3
            or base_params[2].type_index != entity_params[4].type_index
            or image.metadata.metadata_type_name(base_params[0].type_index) != "System.UInt64"
            or image.metadata.metadata_type_name(base_params[1].type_index) != "System.Int32"):
        raise DynamicRootCompError("visibility Register grid/index argument types differ")
    for kind in ("state", "area"):
        getter = image.metadata.methods[int(selected[f"{kind}GroupMethodIndex"])]
        params = image.metadata.parameters_for(getter)
        if (len(params) != 2 or params[0].type_index != base_params[2].type_index
                or image.metadata.metadata_type_name(params[1].type_index) != "System.Int32"):
            raise DynamicRootCompError(f"{kind} GetValidIndexGroup arguments differ")
    root_vector = next(row for row in main_layout["vectors"]
                       if int(row["fieldIndex"]) == int(layout["rootCompFieldIndex"]))
    primitive_vector = next(row for row in main_layout["vectors"]
                            if int(row["fieldIndex"]) == int(layout["visibleDesc"]["vectorFieldIndex"]))
    helper_rva = int(selected["primitiveHelperRva"])
    helper = image.pe.bytes_at_va(image.pe.image_base + helper_rva,
                                  int(selected["primitiveHelperWindowLength"]))
    if hashlib.sha256(helper).hexdigest().upper() != selected["primitiveHelperWindowSha256"].upper():
        raise DynamicRootCompError("visibility PrimitiveIntList native helper code window differs")
    index_getter_index = next(int(row["getterMethodIndex"]) for row in index_layout["fields"]
                              if row["name"] == "Index")
    _validate_visibility_code(
        selected,
        register_entity=raw_methods[register_entity.index],
        register_entity_rva=int(methods[register_entity.index]["rva"]),
        controller_register=raw_methods[base_register.index],
        controller_register_rva=int(methods[base_register.index]["rva"]),
        state_getter=raw_methods[int(selected["stateGroupMethodIndex"])],
        area_getter=raw_methods[int(selected["areaGroupMethodIndex"])],
        primitive_helper=helper,
        root_slot=int(root_vector["vtableSlot"]), root_width=int(layout["rootCompWidth"]),
        visible_offset=int(layout["rootCompVisibleDescOffset"]),
        area_offset=int(layout["visibleDesc"]["visibleAreaGroupOffset"]),
        primitive_slot=int(primitive_vector["vtableSlot"]),
        group_num_rva=int(methods[int(layout["groupNumGetterMethodIndex"])]["rva"]),
        index_getter_rva=image.method_pointer_va(image.metadata.methods[index_getter_index]) - image.pe.image_base,
    )


def validate_native_layout(
    gameassembly: Path, metadata: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[int, str], dict[int, str], dict[str, str], dict[str, str]]:
    """Authenticate local methods, the two dependent layouts and the route."""
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="dynamic_root_comp", status="validated")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicRootCompError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = Path(gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file():
        raise DynamicRootCompError(f"installed_native_inputs:missing:{unity}")
    unity_sha = sha256_file(unity).upper()
    if unity_sha != inputs["unityPlayerSha256"].upper():
        raise DynamicRootCompError("installed_native_inputs:mismatched:UnityPlayer.dll hash differs")
    receipt = {
        "gameAssemblySha256": gate.gameassembly_sha256.upper(),
        "metadataSha256": gate.metadata_sha256.upper(),
        "unityPlayerSha256": unity_sha,
    }
    index_layout, main_layout, enum_by_id, index_digest, main_digest, index_receipt = validate_data_index_layout(
        gameassembly, metadata,
    )
    _routes, route_enum, _system_enum, route_digest, route_receipt = validate_native_routes(
        gameassembly, metadata,
    )
    if receipt != index_receipt or receipt != route_receipt or enum_by_id != route_enum:
        raise DynamicRootCompError("RootComp, DataIndex, and route contracts select different native evidence")
    route_contract, reread_digest = read_reviewed_contract(
        ROUTE_CONTRACT, schema=ROUTE_SCHEMA, label="dynamic_system_routing", status="validated",
    )
    if reread_digest != route_digest:
        raise DynamicRootCompError("selected route contract changed during validation")

    layout = contract["layout"]
    vectors = {int(row["fieldIndex"]): row for row in main_layout["vectors"]}
    root_vector = vectors.get(int(layout["rootCompFieldIndex"]))
    directory_vector = vectors.get(int(layout["dataIndexFieldIndex"]))
    visible = layout["visibleDesc"]
    primitive_vector = vectors.get(int(visible["vectorFieldIndex"]))
    if (layout["gridType"] != main_layout["gridType"] or root_vector is None
            or root_vector["name"] != "RootComp"
            or root_vector["elementType"] != layout["rootCompType"]
            or int(root_vector["elementWidth"]) != int(layout["rootCompWidth"])
            or int(root_vector["elementAlignment"]) != int(layout["rootCompAlignment"])):
        raise DynamicRootCompError("RootComp main vector binding differs")
    if (directory_vector is None or directory_vector["name"] != "DataIndex"
            or directory_vector["elementType"] != layout["dataIndexType"]
            or int(directory_vector["elementWidth"]) != int(layout["dataIndexWidth"])
            or int(layout["dataIndexFieldIndex"]) != int(index_layout["dataIndexFieldIndex"])
            or int(layout["dataIndexWidth"]) != int(index_layout["recordWidth"])):
        raise DynamicRootCompError("DataIndex directory binding differs")
    if enum_by_id.get(int(layout["directoryTypeValue"])) != "DataIndex":
        raise DynamicRootCompError("selected EDynamicSceneData.DataIndex value differs")
    if (primitive_vector is None or primitive_vector["name"] != visible["vectorName"]
            or primitive_vector["elementType"] != "System.Int32"
            or int(primitive_vector["elementWidth"]) != 4
            or enum_by_id.get(int(visible["dataTypeValue"])) != "PrimitiveInt"):
        raise DynamicRootCompError("visible-group PrimitiveIntList vector/enum binding differs")

    image = open_native_image(Path(gameassembly), Path(metadata))
    entity_enum_rows = native_enum_members(
        image.metadata, field_defaults(image.metadata), image.pe, image.registration,
        layout["entityEnumType"],
    )
    entity_enum = {int(row["id"]): row["name"] for row in entity_enum_rows}
    if len(entity_enum) != len(entity_enum_rows) or len(set(entity_enum.values())) != len(entity_enum_rows):
        raise DynamicRootCompError("EDynamicSceneEntityType enum has duplicate IDs or names")
    methods: dict[int, dict[str, Any]] = {}
    raw_methods: dict[int, bytes] = {}
    for row in contract["methods"]:
        index = int(row["index"])
        if index in methods:
            raise DynamicRootCompError(f"duplicate RootComp method index {index}")
        image.validate_method_row([index, row["type"], row["method"], int(row["rva"])], label="dynamic_root_comp")
        method = image.metadata.methods[index]
        params = [image.metadata.metadata_type_name(p.type_index) for p in image.metadata.parameters_for(method)]
        result = image.metadata.metadata_type_name(method.return_type)
        if params != row["parameters"] or result != row["returnType"]:
            raise DynamicRootCompError(f"method signature differs: {row['type']}.{row['method']}")
        raw = image.pe.bytes_at_va(image.pe.image_base + int(row["rva"]), int(row["bodyExtent"]))
        if hashlib.sha256(raw).hexdigest().upper() != row["bodySha256"].upper():
            raise DynamicRootCompError(f"method code window differs: {row['type']}.{row['method']}")
        methods[index], raw_methods[index] = row, raw
    bindings = {
        "gridLifecycleDataTypeMethodIndex": ("Beyond.Gameplay.Core.DynamicScene.DynamicSceneDynamicEntitySystem", "get_gridLifecycleDataType"),
        "templateLookup.onInitMethodIndex": ("Beyond.Gameplay.Core.DynamicScene.DynamicSceneDynamicEntitySystem", "OnInit"),
        "onGridEnterMethodIndex": ("Beyond.Gameplay.Core.DynamicScene.DynamicSceneDynamicEntitySystem", "OnDynamicEntityGridEnter"),
        "onGridLoadMethodIndex": ("Beyond.Gameplay.Core.DynamicScene.DynamicSceneDynamicEntitySystem", "OnRootCompGridLoad"),
        "onGridReloadMethodIndex": ("Beyond.Gameplay.Core.DynamicScene.DynamicSceneDynamicEntitySystem", "OnRootCompGridReLoad"),
        "registerEntitiesMethodIndex": ("Beyond.Gameplay.Core.DynamicScene.DynamicSceneDynamicEntitySystem", "_RegisterEntities"),
        "registerEntityMethodIndex": ("Beyond.Gameplay.Core.DynamicScene.DynamicSceneEntitySystem", "RegisterEntity"),
        "rootCompBuilderMethodIndex": (layout["rootCompType"], "CreateFBDynamicSceneRootComp"),
        "rootCompTypeGetterMethodIndex": (layout["rootCompType"], "get_Type"),
        "rootCompStateGetterMethodIndex": (layout["rootCompType"], "get_State"),
        "compsGetterMethodIndex": (layout["rootCompType"], "get_Comps"),
        "rootCompNeedLazyDestroyGetterMethodIndex": (layout["rootCompType"], "get_NeedLazyDestroy"),
        "rootCompVisibleDescGetterMethodIndex": (layout["rootCompType"], "get_VisibleDesc"),
        "visibleDesc.builderMethodIndex": (visible["type"], "CreateFBDynamicSceneVisibleDesc"),
        "visibleDesc.visibleStateGetterMethodIndex": (visible["type"], "get_VisibleStateGroup"),
        "visibleDesc.visibleAreaGetterMethodIndex": (visible["type"], "get_VisibleAreaGroup"),
        "groupBuilderMethodIndex": (layout["groupType"], "CreateFBDynamicSceneDataGroup"),
        "groupIndexGetterMethodIndex": (layout["groupType"], "get_Index"),
        "groupNumGetterMethodIndex": (layout["groupType"], "get_Num"),
        "groupTotalGetterMethodIndex": (layout["groupType"], "get_TotalInGrid"),
        "idCompPath.uniqueIdGetterMethodIndex": (layout["idCompPath"]["vectorType"], "get_UniqueId"),
        "visibilityConsumer.baseRegisterMethodIndex": (layout["visibilityConsumer"]["baseControllerType"], "Register"),
        "visibilityConsumer.stateGroupMethodIndex": (layout["visibilityConsumer"]["stateControllerType"], "GetValidIndexGroup"),
        "visibilityConsumer.areaGroupMethodIndex": (layout["visibilityConsumer"]["areaControllerType"], "GetValidIndexGroup"),
        "parseLoadMethodIndex": ("Beyond.Gameplay.Core.DynamicScene.DynamicSceneDynamicEntitySystem", "_ParseLoad"),
    }
    def method_index(key: str) -> int:
        if "." in key:
            group, field = key.split(".", 1)
            return int(layout[group][field])
        return int(layout[key])

    if set(methods) != {method_index(key) for key in bindings}:
        raise DynamicRootCompError("RootComp native method set differs")
    for key, identity in bindings.items():
        row = methods[method_index(key)]
        if (row["type"], row["method"]) != identity:
            raise DynamicRootCompError(f"RootComp method binding differs: {key}")
    for key, result in (
        ("rootCompTypeGetterMethodIndex", "System.Int32"),
        ("rootCompStateGetterMethodIndex", "System.UInt32"),
        ("compsGetterMethodIndex", layout["groupType"]),
        ("rootCompNeedLazyDestroyGetterMethodIndex", "System.Boolean"),
        ("rootCompVisibleDescGetterMethodIndex", visible["type"]),
        ("groupIndexGetterMethodIndex", layout["dataIndexType"]),
        ("groupNumGetterMethodIndex", "System.Int32"),
        ("groupTotalGetterMethodIndex", "System.Int32"),
    ):
        row = methods[int(layout[key])]
        if row["parameters"] or row["returnType"] != result:
            raise DynamicRootCompError(f"RootComp getter signature differs: {key}")
    for key in ("visibleStateGetterMethodIndex", "visibleAreaGetterMethodIndex"):
        row = methods[int(visible[key])]
        if row["parameters"] or row["returnType"] != layout["groupType"]:
            raise DynamicRootCompError(f"VisibleDesc getter signature differs: {key}")
    if methods[int(layout["parseLoadMethodIndex"])]["returnType"] != "System.Void":
        raise DynamicRootCompError("_ParseLoad return type differs")
    lifecycle_type = methods[int(layout["gridLifecycleDataTypeMethodIndex"])]
    if lifecycle_type["parameters"] or lifecycle_type["returnType"] != index_layout["enumType"]:
        raise DynamicRootCompError("grid lifecycle data type signature differs")
    for key in ("onGridLoadMethodIndex", "onGridReloadMethodIndex"):
        row = methods[int(layout[key])]
        if row["parameters"] != ["System.UInt32", "System.UInt16"] or row["returnType"] != "System.Void":
            raise DynamicRootCompError(f"{row['method']} signature differs")
    registration = methods[int(layout["registerEntityMethodIndex"])]
    if (registration["parameters"][:3] != [
        "System.UInt64", "Beyond.Gameplay.Core.DynamicScene.EDynamicSystem",
        "Beyond.Gameplay.Core.DynamicScene.EDynamicSystem",
    ] or len(registration["parameters"]) != 5 or registration["returnType"] != "System.UInt64"):
        raise DynamicRootCompError("RegisterEntity typed signature differs")

    root_builder = raw_methods[int(layout["rootCompBuilderMethodIndex"])]
    group_builder = raw_methods[int(layout["groupBuilderMethodIndex"])]
    if (_byte_after(root_builder, b"\x45\x8d\x69", "RootComp builder alignment") != int(layout["rootCompAlignment"])
            or _byte_after(root_builder, b"\x45\x8d\x41", "RootComp builder width") != int(layout["rootCompWidth"])):
        raise DynamicRootCompError("RootComp builder size/alignment differs")
    group_start = group_builder.find(b"\x41\x8d\x51")
    if (group_start < 0 or group_builder[group_start + 4:group_start + 7] != b"\x45\x8d\x41"
            or group_builder[group_start + 3] != int(layout["groupAlignment"])
            or group_builder[group_start + 7] != int(layout["groupWidth"])):
        raise DynamicRootCompError("DataGroup builder size/alignment differs")
    comps = raw_methods[int(layout["compsGetterMethodIndex"])]
    root_type_getter = raw_methods[int(layout["rootCompTypeGetterMethodIndex"])]
    if int(layout["rootCompTypeOffset"]) != 0 or _unique(root_type_getter, b"\x8b\x1b", "RootComp.get_Type offset") < 0:
        raise DynamicRootCompError("RootComp.Type offset differs")
    if _byte_after(comps, b"\x83\xc2", "RootComp.get_Comps offset") != int(layout["compsOffset"]):
        raise DynamicRootCompError("RootComp.Comps offset differs")
    state = raw_methods[int(layout["rootCompStateGetterMethodIndex"])]
    lazy = raw_methods[int(layout["rootCompNeedLazyDestroyGetterMethodIndex"])]
    root_visible = raw_methods[int(layout["rootCompVisibleDescGetterMethodIndex"])]
    if (_instruction(state, int(layout["rootCompStateGetterCodeOffset"]),
                     b"\x8d\x53", "RootComp.get_State offset") != int(layout["rootCompStateOffset"])
            or _instruction(lazy, int(layout["rootCompNeedLazyDestroyGetterCodeOffset"]),
                            b"\x8d\x53", "RootComp.get_NeedLazyDestroy offset")
            != int(layout["rootCompNeedLazyDestroyOffset"])
            or _instruction(root_visible, int(layout["rootCompVisibleDescGetterCodeOffset"]),
                            b"\x83\xc2", "RootComp.get_VisibleDesc offset")
            != int(layout["rootCompVisibleDescOffset"])):
        raise DynamicRootCompError("RootComp State/LazyDestroy/VisibleDesc offsets differ")
    visible_builder = raw_methods[int(visible["builderMethodIndex"])]
    visible_state = raw_methods[int(visible["visibleStateGetterMethodIndex"])]
    visible_area = raw_methods[int(visible["visibleAreaGetterMethodIndex"])]
    state_read = int(visible["visibleStateBaseReadOffset"])
    state_call = int(visible["visibleStateCallOffset"])
    if (_byte_after(visible_builder, b"\x45\x8d\x41", "VisibleDesc builder width")
            != int(visible["width"]) or visible_state[state_read:state_read + 2] != b"\x8b\x17"
            or visible_state[state_call] != 0xE8
            or b"\x83\xc2" in visible_state[state_read + 2:state_call]
            or int(visible["visibleStateGroupOffset"]) != 0
            or _instruction(visible_area, int(visible["visibleAreaGetterCodeOffset"]),
                            b"\x83\xc2", "VisibleDesc.get_VisibleAreaGroup offset")
            != int(visible["visibleAreaGroupOffset"])):
        raise DynamicRootCompError("VisibleDesc group width/offsets differ")
    group_index = raw_methods[int(layout["groupIndexGetterMethodIndex"])]
    if (int(layout["groupIndexOffset"]) != 0 or b"\x8b\x17" not in group_index
            or b"\x0f\x10\x47\x08" not in group_index):
        raise DynamicRootCompError("DataGroup.Index inline offset differs")
    group_num = raw_methods[int(layout["groupNumGetterMethodIndex"])]
    if _byte_after(group_num, b"\x8d\x7e", "DataGroup.get_Num offset") != int(layout["groupNumOffset"]):
        raise DynamicRootCompError("DataGroup.Num offset differs")
    group_total = raw_methods[int(layout["groupTotalGetterMethodIndex"])]
    if _byte_after(group_total, b"\x8d\x53", "DataGroup.get_TotalInGrid offset") != int(layout["groupTotalOffset"]):
        raise DynamicRootCompError("DataGroup.TotalInGrid offset differs")
    if (int(layout["compsOffset"]) + int(layout["groupWidth"]) > int(layout["rootCompWidth"])
            or int(layout["rootCompStateOffset"]) != int(layout["rootCompTypeOffset"]) + 4
            or int(layout["compsOffset"]) != int(layout["rootCompStateOffset"]) + 4
            or int(layout["rootCompNeedLazyDestroyOffset"]) != int(layout["compsOffset"]) + int(layout["groupWidth"])
            or int(layout["rootCompVisibleDescOffset"]) != int(layout["rootCompNeedLazyDestroyOffset"]) + 4
            or int(layout["rootCompVisibleDescOffset"]) + int(visible["width"]) != int(layout["rootCompWidth"])
            or int(visible["visibleAreaGroupOffset"]) != int(visible["visibleStateGroupOffset"]) + int(layout["groupWidth"])
            or int(visible["visibleAreaGroupOffset"]) + int(layout["groupWidth"]) != int(visible["width"])
            or int(layout["groupIndexOffset"]) + int(layout["dataIndexWidth"]) > int(layout["groupWidth"])
            or int(layout["groupNumOffset"]) != int(layout["groupIndexOffset"]) + int(layout["dataIndexWidth"])
            or int(layout["groupTotalOffset"]) != int(layout["groupNumOffset"]) + 4
            or int(layout["groupTotalOffset"]) + 4 != int(layout["groupWidth"])):
        raise DynamicRootCompError("nested RootComp field span exceeds selected struct width")

    consumer = layout["consumer"]
    parse_row = methods[int(layout["parseLoadMethodIndex"])]
    parse_raw = raw_methods[parse_row["index"]]
    if _mov_edx_imm32(parse_raw, int(consumer["rootCompSlotOffset"]), "_ParseLoad RootComp slot") != int(root_vector["vtableSlot"]):
        raise DynamicRootCompError("_ParseLoad RootComp slot differs")
    if _instruction(parse_raw, int(consumer["rootCompStrideOffset"]), b"\x6b\xd3", "_ParseLoad RootComp stride") != int(layout["rootCompWidth"]):
        raise DynamicRootCompError("_ParseLoad RootComp stride differs")
    type_read = int(consumer["rootCompTypeFieldReadOffset"])
    if parse_raw[type_read:type_read + 4] != b"\x8b\x54\x24\x78":
        raise DynamicRootCompError("_ParseLoad RootComp.Type field read differs")
    getter_row = methods[int(layout["rootCompTypeGetterMethodIndex"])]
    getter_reader = _call_target(
        root_type_getter, int(consumer["rootCompTypeGetterCallOffset"]),
        int(getter_row["rva"]), "RootComp.get_Type scalar reader",
    )
    if _call_target(
        parse_raw, int(consumer["rootCompTypeAccessorCallOffset"]), int(parse_row["rva"]),
        "_ParseLoad RootComp.Type scalar reader",
    ) != getter_reader:
        raise DynamicRootCompError("_ParseLoad RootComp.Type reader differs from generated getter")
    if _instruction(parse_raw, int(consumer["compsOffsetCodeOffset"]), b"\x41\x8d\x56", "_ParseLoad Comps offset") != int(layout["compsOffset"]):
        raise DynamicRootCompError("_ParseLoad Comps offset differs")
    if _mov_edx_imm32(parse_raw, int(consumer["dataIndexSlotOffset"]), "_ParseLoad DataIndex slot") != int(directory_vector["vtableSlot"]):
        raise DynamicRootCompError("_ParseLoad DataIndex slot differs")
    if parse_raw[int(consumer["dataIndexAddOffset"]):int(consumer["dataIndexAddOffset"]) + 3] != b"\x8d\x14\x1e":
        raise DynamicRootCompError("_ParseLoad DataGroup start plus loop offset differs")
    if _instruction(parse_raw, int(consumer["dataIndexStrideOffset"]), b"\xc1\xe2", "_ParseLoad DataIndex stride") != 4:
        raise DynamicRootCompError("_ParseLoad DataIndex stride differs")
    if 1 << 4 != int(layout["dataIndexWidth"]):
        raise DynamicRootCompError("_ParseLoad DataIndex stride does not match selected width")
    index_methods = {row["name"]: row for row in index_layout["fields"]}
    call_checks = (
        ("groupIndexGetterCallOffset", image.method_pointer_va(image.metadata.methods[int(index_methods["Index"]["getterMethodIndex"])]) - image.pe.image_base, "DataIndex.get_Index"),
        ("dataIndexTypeGetterCallOffset", image.method_pointer_va(image.metadata.methods[int(index_methods["Type"]["getterMethodIndex"])]) - image.pe.image_base, "DataIndex.get_Type"),
        ("routeCallOffset", int(route_contract["layout"]["calledRoute"]["rva"]), "selected system route"),
    )
    steps = (
        "rootCompSlotOffset", "rootCompStrideOffset", "rootCompTypeFieldReadOffset",
        "rootCompTypeAccessorCallOffset", "compsOffsetCodeOffset",
        "groupIndexGetterCallOffset", "dataIndexSlotOffset", "dataIndexAddOffset",
        "dataIndexStrideOffset", "dataIndexTypeGetterCallOffset", "routeCallOffset",
    )
    offsets = [int(consumer[key]) for key in steps]
    if offsets != sorted(set(offsets)):
        raise DynamicRootCompError("_ParseLoad selected consumer steps are out of order")
    for key, target, label in call_checks:
        if _call_target(parse_raw, int(consumer[key]), int(parse_row["rva"]), label) != target:
            raise DynamicRootCompError(f"_ParseLoad {label} call target differs")
    _call_target(
        parse_raw, int(consumer["innerCountCallOffset"]), int(parse_row["rva"]),
        "_ParseLoad inner loop count",
    )
    count_store = int(consumer["innerCountStoreOffset"])
    if parse_raw[count_store:count_store + 4] != b"\x89\x44\x24\x70":
        raise DynamicRootCompError("_ParseLoad inner loop count storage differs")
    inner_comparison = int(consumer["innerLoopCompareOffset"])
    if parse_raw[inner_comparison:inner_comparison + 4] != b"\x3b\x74\x24\x70":
        raise DynamicRootCompError("_ParseLoad inner loop count comparison differs")
    inner_branch = int(consumer["innerLoopBranchOffset"])
    if parse_raw[inner_branch:inner_branch + 2] != b"\x0f\x8c":
        raise DynamicRootCompError("_ParseLoad inner loop branch differs")
    inner_target = inner_branch + 6 + struct.unpack_from("<i", parse_raw, inner_branch + 2)[0]
    if inner_target != int(consumer["innerLoopHeadOffset"]):
        raise DynamicRootCompError("_ParseLoad inner loop target differs")
    lifecycle = layout["lifecycle"]
    lifecycle_raw = raw_methods[int(layout["gridLifecycleDataTypeMethodIndex"])]
    lifecycle_data_id = _mov_eax_imm32(
        lifecycle_raw, int(lifecycle["gridLifecycleTypeReturnOffset"]),
        "grid lifecycle data type",
    )
    if enum_by_id.get(lifecycle_data_id) != "RootComp":
        raise DynamicRootCompError("grid lifecycle data type is not EDynamicSceneData.RootComp")
    parse_rva = int(parse_row["rva"])
    register_rva = int(methods[int(layout["registerEntitiesMethodIndex"])]["rva"])
    for key, slot_key, count_key, call_key in (
        ("onGridLoadMethodIndex", "gridLoadRootCompSlotOffset", "gridLoadCountStackOffset", "gridLoadRegisterEntitiesCallOffset"),
        ("onGridReloadMethodIndex", None, "gridReloadCountStackOffset", "gridReloadRegisterEntitiesCallOffset"),
    ):
        row = methods[int(layout[key])]
        raw = raw_methods[row["index"]]
        if slot_key is not None and _mov_edx_imm32(raw, int(lifecycle[slot_key]), row["method"] + " RootComp slot") != int(root_vector["vtableSlot"]):
            raise DynamicRootCompError(f"{row['method']} RootComp vector slot differs")
        count_offset = int(lifecycle[count_key])
        if raw[count_offset:count_offset + 4] != b"\x89\x44\x24\x20":
            raise DynamicRootCompError(f"{row['method']} passed count differs")
        if _call_target(raw, int(lifecycle[call_key]), int(row["rva"]), row["method"] + " registration") != register_rva:
            raise DynamicRootCompError(f"{row['method']} does not call _RegisterEntities")
    register_row = methods[int(layout["registerEntitiesMethodIndex"])]
    register_raw = raw_methods[register_row["index"]]
    if _mov_edx_imm32(
        register_raw, int(lifecycle["registerEntitiesRootCompSlotOffset"]),
        "_RegisterEntities RootComp slot",
    ) != int(root_vector["vtableSlot"]):
        raise DynamicRootCompError("_RegisterEntities RootComp vector slot differs")
    count_read = int(lifecycle["registerEntitiesCountReadOffset"])
    if register_raw[count_read:count_read + 8] != b"\x44\x8b\xa4\x24\xf0\x00\x00\x00":
        raise DynamicRootCompError("_RegisterEntities count parameter read differs")
    if _instruction(
        register_raw, int(lifecycle["registerEntitiesRootCompStrideOffset"]),
        b"\x41\x83\xc6", "_RegisterEntities RootComp stride",
    ) != int(layout["rootCompWidth"]):
        raise DynamicRootCompError("_RegisterEntities RootComp stride differs")
    comparison = int(lifecycle["registerEntitiesLoopCompareOffset"])
    if register_raw[comparison:comparison + 3] != b"\x41\x3b\xf4":
        raise DynamicRootCompError("_RegisterEntities count loop comparison differs")
    branch = int(lifecycle["registerEntitiesLoopBranchOffset"])
    if register_raw[branch:branch + 2] != b"\x0f\x8c":
        raise DynamicRootCompError("_RegisterEntities loop branch differs")
    branch_target = branch + 6 + struct.unpack_from("<i", register_raw, branch + 2)[0]
    if branch_target != int(lifecycle["registerEntitiesLoopHeadOffset"]):
        raise DynamicRootCompError("_RegisterEntities loop target differs")
    if _call_target(
        register_raw, int(lifecycle["registerEntitiesParseLoadCallOffset"]),
        int(register_row["rva"]), "_RegisterEntities _ParseLoad",
    ) != parse_rva:
        raise DynamicRootCompError("_RegisterEntities does not call _ParseLoad")
    enter_row = methods[int(layout["onGridEnterMethodIndex"])]
    if _call_target(
        raw_methods[enter_row["index"]], int(lifecycle["gridEnterParseLoadCallOffset"]),
        int(enter_row["rva"]), "OnDynamicEntityGridEnter _ParseLoad",
    ) != parse_rva:
        raise DynamicRootCompError("OnDynamicEntityGridEnter does not call _ParseLoad")
    if _call_target(
        parse_raw, int(lifecycle["parseLoadRegisterEntityCallOffset"]), parse_rva,
        "_ParseLoad RegisterEntity",
    ) != int(registration["rva"]):
        raise DynamicRootCompError("_ParseLoad does not call RegisterEntity")
    _validate_template_lookup(image, layout, methods, raw_methods)
    _validate_id_comp_path(image, layout, main_layout, index_layout, enum_by_id, methods, raw_methods)
    _validate_visibility_consumer(image, layout, main_layout, index_layout, methods, raw_methods)
    digests = {
        "rootCompContractSha256": digest,
        "dataIndexContractSha256": index_digest,
        "mainVectorContractSha256": main_digest,
        "systemRouteContractSha256": route_digest,
    }
    return layout, index_layout, main_layout, enum_by_id, entity_enum, digests, receipt


def _grid_groups(
    data: bytes, *, source: str, ordinal: int,
    unique_id: int, root_body: int, root_count: int, directory_body: int, directory_count: int,
    layout: dict[str, Any], index_layout: dict[str, Any], entity_enum: dict[int, str],
) -> tuple[int, int, Counter[int], dict[int, tuple[int, ...]]]:
    """Check one grid's group spans and ordered directory type signatures."""
    fields = {row["name"]: row for row in index_layout["fields"]}
    spans: list[tuple[int, int]] = []
    entity_types: Counter[int] = Counter()
    signatures: dict[int, tuple[int, ...]] = {}
    for group_ordinal in range(root_count):
        root_start = root_body + group_ordinal * int(layout["rootCompWidth"])
        entity_type = struct.unpack_from("<i", data, root_start + int(layout["rootCompTypeOffset"]))[0]
        if entity_type not in entity_enum:
            raise DynamicRootCompError(
                f"{source}: grid[{ordinal}] UniqueId={unique_id} RootComp[{group_ordinal}] "
                f"Type={entity_type} has no selected EDynamicSceneEntityType numeric member"
            )
        entity_types[entity_type] += 1
        group_start = root_start + int(layout["compsOffset"])
        index_start = group_start + int(layout["groupIndexOffset"])
        values = {
            name: struct.unpack_from(FIELD_FORMATS[field["type"]], data, index_start + int(field["offset"]))[0]
            for name, field in fields.items()
        }
        label = f"{source}: grid[{ordinal}] UniqueId={unique_id} RootComp[{group_ordinal}].Comps"
        if (values["IsInvalid"] != 0 or values["Type"] != int(layout["directoryTypeValue"])
                or values["Grid"] != unique_id):
            raise DynamicRootCompError(
                f"{label}.Index expected (IsInvalid=0, Type={layout['directoryTypeValue']}/DataIndex, Grid={unique_id}), "
                f"actual=({values['IsInvalid']}, {values['Type']}, {values['Grid']})"
            )
        num = struct.unpack_from("<i", data, group_start + int(layout["groupNumOffset"]))[0]
        total = struct.unpack_from("<i", data, group_start + int(layout["groupTotalOffset"]))[0]
        start = values["Index"]
        if num <= 0 or start < 0 or start + num > directory_count or total != directory_count:
            raise DynamicRootCompError(
                f"{label} span expected 0<=Index, Num>0, Index+Num<=DataIndexCount={directory_count}, "
                f"TotalInGrid={directory_count}; actual Index={start} Num={num} TotalInGrid={total}"
            )
        type_field = fields["Type"]
        signature = tuple(
            struct.unpack_from(
                FIELD_FORMATS[type_field["type"]], data,
                directory_body + position * int(layout["dataIndexWidth"]) + int(type_field["offset"]),
            )[0]
            for position in range(start, start + num)
        )
        previous = signatures.setdefault(entity_type, signature)
        if previous != signature:
            raise DynamicRootCompError(
                f"{label} Type={entity_type}/{entity_enum[entity_type]} component signature differs: "
                f"expected={previous} actual={signature}"
            )
        spans.append((start, start + num))
    cursor = 0
    for start, end in sorted(spans):
        if start != cursor:
            raise DynamicRootCompError(
                f"{source}: grid[{ordinal}] UniqueId={unique_id} RootComp spans do not tile "
                f"DataIndex: expected next Index={cursor}, actual={start} end={end} "
                f"groups={root_count} directoryCount={directory_count}"
            )
        cursor = end
    if cursor != directory_count:
        raise DynamicRootCompError(
            f"{source}: grid[{ordinal}] UniqueId={unique_id} RootComp spans do not tile "
            f"DataIndex: covered={cursor} directoryCount={directory_count} groups={root_count}"
        )
    return root_count, cursor, entity_types, signatures


def _grid_visible_groups(
    data: bytes, *, source: str, ordinal: int, unique_id: int,
    root_body: int, root_count: int, primitive_body: int, primitive_count: int,
    layout: dict[str, Any], index_layout: dict[str, Any],
) -> tuple[Counter[str], dict[str, Counter[int]]]:
    """Check both nested DataGroup spans against one grid's PrimitiveIntList."""
    visible = layout["visibleDesc"]
    fields = {row["name"]: row for row in index_layout["fields"]}
    counts: Counter[str] = Counter({"primitiveIntEntries": primitive_count})
    values: dict[str, Counter[int]] = {
        "rootState": Counter(), "needLazyDestroy": Counter(),
        "visibleState": Counter(), "visibleArea": Counter(),
    }
    spans: list[tuple[int, int, str]] = []
    for group_ordinal in range(root_count):
        root_start = root_body + group_ordinal * int(layout["rootCompWidth"])
        label = f"{source}: grid[{ordinal}] UniqueId={unique_id} RootComp[{group_ordinal}]"
        state = struct.unpack_from("<I", data, root_start + int(layout["rootCompStateOffset"]))[0]
        lazy = data[root_start + int(layout["rootCompNeedLazyDestroyOffset"])]
        if lazy not in (0, 1):
            raise DynamicRootCompError(f"{label}.NeedLazyDestroy invalid Boolean={lazy}")
        values["rootState"][state] += 1
        values["needLazyDestroy"][lazy] += 1
        if data[root_start + int(layout["rootCompNeedLazyDestroyOffset"]) + 1:
                root_start + int(layout["rootCompVisibleDescOffset"])] != b"\x00" * 3:
            counts["nonzeroRootPadding"] += 1
        desc_start = root_start + int(layout["rootCompVisibleDescOffset"])
        for name, group_offset in (
            ("visibleState", int(visible["visibleStateGroupOffset"])),
            ("visibleArea", int(visible["visibleAreaGroupOffset"])),
        ):
            group_start = desc_start + group_offset
            index_start = group_start + int(layout["groupIndexOffset"])
            fields_found = {
                field_name: struct.unpack_from(FIELD_FORMATS[field["type"]], data,
                                               index_start + int(field["offset"]))[0]
                for field_name, field in fields.items()
            }
            group_label = f"{label}.VisibleDesc.{name}Group"
            invalid = fields_found["IsInvalid"]
            if invalid not in (0, 1):
                raise DynamicRootCompError(f"{group_label}.Index invalid Boolean={invalid}")
            if (fields_found["Type"] != int(visible["dataTypeValue"])
                    or fields_found["Grid"] != unique_id):
                raise DynamicRootCompError(
                    f"{group_label}.Index expected Type={visible['dataTypeValue']}/PrimitiveInt, "
                    f"Grid={unique_id}; actual Type={fields_found['Type']} Grid={fields_found['Grid']}"
                )
            num = struct.unpack_from("<i", data, group_start + int(layout["groupNumOffset"]))[0]
            total = struct.unpack_from("<i", data, group_start + int(layout["groupTotalOffset"]))[0]
            start = fields_found["Index"]
            if (start < 0 or num < 0 or start + num > primitive_count
                    or total != primitive_count or bool(invalid) == bool(num)):
                raise DynamicRootCompError(
                    f"{group_label} PrimitiveIntList span expected 0<=Index, "
                    f"0<=Num, Index+Num<=count={primitive_count}, TotalInGrid={primitive_count}, "
                    f"IsInvalid iff Num=0; actual IsInvalid={invalid} Index={start} "
                    f"Num={num} TotalInGrid={total}"
                )
            counts[name + "Records"] += 1
            if data[index_start + 1:index_start + 4] != b"\x00\x00\x00":
                counts["nonzeroVisibleIndexPadding"] += 1
            if not invalid:
                counts[name + "Nonempty"] += 1
                spans.append((start, start + num, group_label))
                for position in range(start, start + num):
                    value = struct.unpack_from("<i", data, primitive_body + position * 4)[0]
                    values[name][value] += 1
    previous_end = 0
    previous_label = ""
    for start, end, label in sorted(spans):
        if start < previous_end:
            raise DynamicRootCompError(
                f"{label} PrimitiveIntList span overlaps {previous_label}: "
                f"Index={start} end={end} previousEnd={previous_end}"
            )
        previous_end, previous_label = end, label
    counts["visibleReferencedInts"] = sum(end - start for start, end, _ in spans)
    counts["visibleUnreferencedInts"] = primitive_count - counts["visibleReferencedInts"]
    return counts, values


def _json_field_line(line: str) -> tuple[str, Any]:
    key, separator, value = line.strip().rstrip(",").partition(":")
    if not separator:
        raise DynamicRootCompError("asset map entry has no key/value separator")
    return json.loads(key), json.loads(value.strip())


def _template_asset_map_row(path: Path, container: str) -> dict[str, Any]:
    """Read only the matching object from a large generated asset map."""
    matches: list[dict[str, Any]] = []
    preceding = ""
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            if line.lstrip().startswith('"Container":'):
                key, value = _json_field_line(line)
                if key != "Container":
                    raise DynamicRootCompError("asset map Container field differs")
                if value.casefold() == container.casefold():
                    name_key, name = _json_field_line(preceding)
                    if name_key != "Name":
                        raise DynamicRootCompError("asset map Name/Container order differs")
                    row: dict[str, Any] = {"Name": name, "Container": value}
                    for field_line in source:
                        if field_line.strip().startswith("}"):
                            break
                        field_key, field_value = _json_field_line(field_line)
                        if field_key in row:
                            raise DynamicRootCompError(f"duplicate asset map field {field_key}")
                        row[field_key] = field_value
                    else:
                        raise DynamicRootCompError("asset map entry is truncated")
                    matches.append(row)
                    preceding = ""
                    continue
            preceding = line
    if len(matches) != 1:
        raise DynamicRootCompError(f"DynamicSceneTemplates asset map match count differs: {len(matches)}")
    return matches[0]


def _template_rows(asset: dict[str, Any], entity_enum: dict[int, str],
                   data_enum: dict[int, str]) -> dict[int, tuple[int, ...]]:
    rows = asset.get("templateDataList")
    if not isinstance(rows, list) or not rows:
        raise DynamicRootCompError("DynamicSceneTemplates.templateDataList is empty or missing")
    templates: dict[int, tuple[int, ...]] = {}
    for ordinal, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"entityType", "comps"}:
            raise DynamicRootCompError(f"DynamicSceneTemplates.templateDataList[{ordinal}] shape differs")
        type_id, comps = row["entityType"], row["comps"]
        if type(type_id) is not int or type_id not in entity_enum:
            raise DynamicRootCompError(f"DynamicSceneTemplates.templateDataList[{ordinal}] has unknown entityType={type_id}")
        if type_id in templates:
            raise DynamicRootCompError(f"DynamicSceneTemplates has duplicate entityType={type_id}/{entity_enum[type_id]}")
        if not isinstance(comps, list) or not comps or any(type(item) is not int or item not in data_enum for item in comps):
            raise DynamicRootCompError(f"DynamicSceneTemplates entityType={type_id}/{entity_enum[type_id]} has invalid comps={comps}")
        templates[type_id] = tuple(comps)
    return templates


def load_current_template_asset(
    selected: dict[str, Any], *, game_root: Path, export_root: Path,
    entity_enum: dict[int, str], data_enum: dict[int, str],
) -> tuple[dict[int, tuple[int, ...]], dict[str, Any]]:
    """Authenticate the exported authored asset against its current source and map."""
    summary = json.loads(DEFAULT_SUMMARY.read_text(encoding="utf-8"))
    if (Path(summary.get("game_root", "")).resolve() != game_root.resolve()
            or Path(summary.get("output_root", "")).resolve() != export_root.resolve()):
        raise DynamicRootCompError("export summary does not select the supplied game/export roots")
    freshness = export_freshness_report(
        game_root=game_root, output_root=export_root, summary_path=DEFAULT_SUMMARY,
        sources=("StreamingAssets",),
    )
    if not freshness.get("fresh"):
        raise DynamicRootCompError(f"DynamicSceneTemplates export freshness failed: {freshness.get('error') or freshness.get('sources')}")
    container = selected["templateAssetPath"].replace("\\", "/").lower()
    map_path = export_root / "meta/StreamingAssets/asset_map/endfield_streamingassets_assets.json"
    asset_map = _template_asset_map_row(map_path, container)
    if asset_map.get("Type") != "MonoBehaviour" or asset_map.get("Name") != "DynamicSceneTemplates":
        raise DynamicRootCompError("DynamicSceneTemplates asset map type/name differs")
    candidates = list((export_root / "game/Unity/MonoBehaviour").glob("DynamicSceneTemplates_p*.json"))
    if len(candidates) != 1:
        raise DynamicRootCompError(f"DynamicSceneTemplates exported object count differs: {len(candidates)}")
    object_path = candidates[0]
    asset = json.loads(object_path.read_text(encoding="utf-8"))
    meta = asset.get("$animestudio")
    if not isinstance(meta, dict) or (meta.get("type"), meta.get("classId"), meta.get("name")) != ("MonoBehaviour", 114, asset_map["Name"]):
        raise DynamicRootCompError("DynamicSceneTemplates exported MonoBehaviour identity differs")
    if (meta.get("pathId") != asset_map.get("PathID")
            or meta.get("sourceOriginalPath") != asset_map.get("Source")
            or meta.get("sourceOffset") != asset_map.get("Offset")
            or meta.get("typeTreeSource") != "serializedType"
            or asset.get("m_Name") != asset_map["Name"]):
        raise DynamicRootCompError("DynamicSceneTemplates object and asset map provenance differ")
    field_paths = set(meta.get("typeTreeFieldPaths") or [])
    required_paths = {
        "templateDataList.Array.data.entityType:UInt8",
        "templateDataList.Array.data.comps.Array.data:int",
    }
    if not required_paths <= field_paths:
        raise DynamicRootCompError("DynamicSceneTemplates serialized type tree lacks template fields")
    if (type(meta.get("byteSize")) is not int or meta["byteSize"] <= 0
            or meta.get("rawDataLength") != meta["byteSize"]
            or not isinstance(meta.get("rawDataSha256"), str)
            or len(meta["rawDataSha256"]) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in meta["rawDataSha256"])):
        raise DynamicRootCompError("DynamicSceneTemplates raw object provenance is incomplete")
    manifest_path = export_root / "meta/StreamingAssets/export_manifest/StreamingAssets_animestudio_json_by_type_MonoBehaviour.jsonl"
    expected_output = "MonoBehaviour/" + object_path.name
    manifest_rows = []
    with manifest_path.open("r", encoding="utf-8") as manifest:
        for line in manifest:
            if object_path.name in line:
                row = json.loads(line)
                if row.get("kind") == "output" and row.get("output") == expected_output:
                    manifest_rows.append(row)
    if len(manifest_rows) != 1:
        raise DynamicRootCompError(f"DynamicSceneTemplates export manifest match count differs: {len(manifest_rows)}")
    manifest_row = manifest_rows[0]
    if (manifest_row.get("pathId") != meta["pathId"]
            or manifest_row.get("serializedFile") != meta.get("sourceFile")
            or manifest_row.get("source") != meta["sourceOriginalPath"]
            or manifest_row.get("sourceOffset") != meta["sourceOffset"]):
        raise DynamicRootCompError("DynamicSceneTemplates export manifest provenance differs")
    source_path = Path(meta["sourceOriginalPath"])
    if not source_path.is_file() or not source_path.resolve().is_relative_to((game_root / "StreamingAssets").resolve()):
        raise DynamicRootCompError("DynamicSceneTemplates source is outside selected installed StreamingAssets")
    if type(meta["sourceOffset"]) is not int or meta["sourceOffset"] < 0 or meta["sourceOffset"] + meta["byteSize"] > source_path.stat().st_size:
        raise DynamicRootCompError("DynamicSceneTemplates source object span exceeds installed VFS file")
    templates = _template_rows(asset, entity_enum, data_enum)
    return templates, {
        "assetPath": selected["templateAssetPath"],
        "exportObject": str(object_path.relative_to(export_root)).replace("\\", "/"),
        "exportObjectSha256": sha256_file(object_path).upper(),
        "source": str(source_path),
        "sourceOffset": meta["sourceOffset"],
        "pathId": meta["pathId"],
        "rawDataSha256": meta.get("rawDataSha256"),
        "streamingAssetsFingerprint": freshness["sources"][0]["current"]["fingerprint"],
        "templateRows": len(templates),
    }


def _require_template_signatures(
    signatures: dict[int, tuple[tuple[int, ...], str]],
    templates: dict[int, tuple[int, ...]], entity_enum: dict[int, str],
) -> None:
    for type_id, (signature, first_source) in signatures.items():
        authored = templates.get(type_id)
        if authored != signature:
            raise DynamicRootCompError(
                f"{first_source} RootComp.Type={type_id}/{entity_enum[type_id]} differs from "
                f"DynamicSceneTemplates: stored={signature} template={authored}"
            )


def audit_current_main(
    layout: dict[str, Any], index_layout: dict[str, Any], main_layout: dict[str, Any],
    enum_by_id: dict[int, str], entity_enum: dict[int, str], *, outer_path: Path, ledger_path: Path, cli_path: Path,
    input_root: Path, expected_input_set_sha256: str,
    templates: dict[int, tuple[int, ...]], template_provenance: dict[str, Any],
) -> dict[str, Any]:
    """Rejoin every current dump to VFS and check all nested group partitions."""
    outer, current_files, provenance = load_current_inputs(
        outer_path, ledger_path, cli_path, expected_input_set_sha256,
        file_name_re=MAIN_NAME_RE, selection_label="fb_main_*.bytes",
    )
    widths = {int(row["fieldIndex"]): int(row["elementWidth"]) for row in main_layout["vectors"]}
    name_to_field = {row["name"]: int(row["fieldIndex"]) for row in main_layout["vectors"]}
    if len(widths) != len(name_to_field):
        raise DynamicRootCompError("duplicate selected SingleGrid vector name")
    totals: Counter[str] = Counter()
    visible_counts: Counter[str] = Counter()
    visible_values: dict[str, Counter[int]] = {
        "rootState": Counter(), "needLazyDestroy": Counter(),
        "visibleState": Counter(), "visibleArea": Counter(),
    }
    entity_types: Counter[int] = Counter()
    signatures: dict[int, tuple[tuple[int, ...], str]] = {}
    id_type = int(layout["idCompPath"]["dataTypeValue"])
    file_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in current_files:
        path = source["path"]
        identity = path.replace("\\", "/").casefold()
        if identity in seen:
            raise DynamicRootCompError(f"duplicate current main path: {path}")
        seen.add(identity)
        data = _checked_dump_path(input_root, path).read_bytes()
        md5 = hashlib.md5(data).hexdigest().upper()
        if len(data) != source["declaredBytes"] or md5 != source["fileDataMd5"]:
            raise DynamicRootCompError(
                f"{path}: dumped bytes differ from authenticated VFS row "
                f"length={len(data)}/{source['declaredBytes']} md5={md5}/{source['fileDataMd5']}"
            )
        try:
            indexed_grids, index_stats = data_index_payload_grids(
                data, widths=widths, layout=index_layout, enum_by_id=enum_by_id,
                name_to_field=name_to_field, source=path,
            )
            root = _root_layout(data)
            grid_body, grid_count, _ = _bounded_vector(data, root, 3, 4)
            if grid_count != len(indexed_grids):
                raise DynamicRootCompError(f"{path}: grid count differs within parser")
            file_groups = file_entries = 0
            file_visible: Counter[str] = Counter()
            for ordinal in range(grid_count):
                slot = grid_body + ordinal * 4
                grid = _table_layout(data, slot + struct.unpack_from("<I", data, slot)[0])
                uid_address = _field_span(data, grid, 0, 4)
                if uid_address is None:
                    raise DynamicRootCompError(f"{path}: grid[{ordinal}] has no UniqueId")
                uid = struct.unpack_from("<I", data, uid_address)[0]
                if uid != indexed_grids[ordinal]["uniqueId"]:
                    raise DynamicRootCompError(f"{path}: grid[{ordinal}] UniqueId differs within parser")
                totals["idCompRecords"] += len(indexed_grids[ordinal]["indexes"].get(id_type, []))
                root_body, root_count, _ = _bounded_vector(
                    data, grid, int(layout["rootCompFieldIndex"]), int(layout["rootCompWidth"]),
                )
                directory_body, directory_count, _ = _bounded_vector(
                    data, grid, int(layout["dataIndexFieldIndex"]), int(layout["dataIndexWidth"]),
                )
                group_count, covered, grid_entity_types, grid_signatures = _grid_groups(
                    data, source=path, ordinal=ordinal, unique_id=uid,
                    root_body=root_body, root_count=root_count,
                    directory_body=directory_body, directory_count=directory_count,
                    layout=layout, index_layout=index_layout, entity_enum=entity_enum,
                )
                primitive_field = int(layout["visibleDesc"]["vectorFieldIndex"])
                primitive_body, primitive_count, _ = _bounded_vector(data, grid, primitive_field, 4)
                if primitive_count != indexed_grids[ordinal]["vectorCounts"][primitive_field]:
                    raise DynamicRootCompError(
                        f"{path}: grid[{ordinal}] UniqueId={uid} PrimitiveIntList count differs within parser"
                    )
                grid_visible, grid_values = _grid_visible_groups(
                    data, source=path, ordinal=ordinal, unique_id=uid,
                    root_body=root_body, root_count=root_count,
                    primitive_body=primitive_body, primitive_count=primitive_count,
                    layout=layout, index_layout=index_layout,
                )
                file_visible.update(grid_visible)
                for name, counts in grid_values.items():
                    visible_values[name].update(counts)
                for type_id, signature in grid_signatures.items():
                    previous = signatures.setdefault(type_id, (signature, f"{path}: grid[{ordinal}] UniqueId={uid}"))
                    if previous[0] != signature:
                        raise DynamicRootCompError(
                            f"{path}: grid[{ordinal}] UniqueId={uid} RootComp.Type={type_id}/{entity_enum[type_id]} "
                            f"component signature differs from {previous[1]}: "
                            f"expected={previous[0]} actual={signature}"
                        )
                file_groups += group_count
                file_entries += covered
                entity_types.update(grid_entity_types)
            totals.update(index_stats)
            totals.update({"files": 1, "bytes": len(data), "groups": file_groups, "coveredDirectoryEntries": file_entries})
            visible_counts.update(file_visible)
            file_rows.append({
                "path": path, "fileDataMd5": md5, "grids": grid_count,
                "groups": file_groups, "coveredDirectoryEntries": file_entries,
                "visibleStateNonempty": file_visible["visibleStateNonempty"],
                "visibleAreaNonempty": file_visible["visibleAreaNonempty"],
            })
        except (ValueError, OverflowError, KeyError, IndexError) as exc:
            raise DynamicRootCompError(f"{path}: RootComp/DataIndex audit failed: {exc}") from exc
    if totals["coveredDirectoryEntries"] != totals["validRecords"] + totals["invalidRecords"]:
        raise DynamicRootCompError("current covered directory count differs from parsed DataIndex records")
    if (visible_counts["visibleStateRecords"] != totals["groups"]
            or visible_counts["visibleAreaRecords"] != totals["groups"]
            or visible_counts["visibleReferencedInts"] + visible_counts["visibleUnreferencedInts"]
            != visible_counts["primitiveIntEntries"]):
        raise DynamicRootCompError("current RootComp visible-group cardinality differs")
    _require_template_signatures(signatures, templates, entity_enum)
    id_group_count = sum(entity_types[type_id] for type_id, (signature, _source) in signatures.items()
                         if id_type in signature)
    id_signature_entries = sum(entity_types[type_id] * signature.count(id_type)
                               for type_id, (signature, _source) in signatures.items())
    if id_signature_entries != totals["idCompRecords"]:
        raise DynamicRootCompError(
            f"current IdComp signature count differs from parsed valid directory rows: "
            f"signature={id_signature_entries} directory={totals['idCompRecords']}"
        )
    return {
        "format": "endfield.dynamic-root-comp-native-audit.v7",
        "status": "validated",
        "inputSetSha256": outer["inputSetSha256"],
        "outer": {
            "reportSha256": provenance["outerReportSha256"],
            "ledgerSha256": provenance["ledgerSha256"],
            "ledgerFileRowCount": provenance["ledgerFileRowCount"],
        },
        "corpus": dict(totals),
        "visibleDesc": {
            "vectorFieldIndex": int(layout["visibleDesc"]["vectorFieldIndex"]),
            "vectorName": layout["visibleDesc"]["vectorName"],
            "dataTypeValue": int(layout["visibleDesc"]["dataTypeValue"]),
            "selectedNativeConsumer": (
                "RegisterEntity passes typed state and area entity controllers to "
                "SceneVisibilityControllerBase.Register. Their GetValidIndexGroup overrides "
                "select the respective RootComp.VisibleDesc group; Register loops over "
                "its Num and Index and reads the grid PrimitiveIntList vector."
            ),
            "counts": dict(visible_counts),
            "values": {
                name: [{"value": value, "count": count} for value, count in sorted(rows.items())]
                for name, rows in visible_values.items()
            },
        },
        "idCompPath": {
            "dataType": id_type, "enumName": enum_by_id[id_type],
            "groupsContaining": id_group_count,
            "directoryEntries": totals["idCompRecords"],
            "selectedNativePath": "read IdComp.UniqueId by DataIndex.Index, then rejoin DataIndex.Type system route",
        },
        "template": {
            **template_provenance,
            "observedMatchingTypes": len(signatures),
            "templateOnlyTypes": [
                {"type": type_id, "enumName": entity_enum[type_id],
                 "componentSignature": [{"type": component, "enumName": enum_by_id[component]}
                                        for component in templates[type_id]]}
                for type_id in sorted(set(templates) - set(signatures))
            ],
        },
        "entityTypes": [
            {
                "type": type_id, "enumName": entity_enum[type_id], "groupCount": count,
                "componentSignature": [
                    {"type": component, "enumName": enum_by_id[component]}
                    for component in signatures[type_id][0]
                ],
            }
            for type_id, count in sorted(entity_types.items())
        ],
        "files": file_rows,
        "evidenceBoundary": {
            "direct": "Selected OnInit passes the compiled DynamicSceneTemplates path through typed TryLoad/Get calls and inserts its list records into the entity template map. _ParseLoad uses RootComp.Type as its key and SafeCount<EDynamicSceneData> on template comps as the inner loop bound. Its selected unpatched IdComp path reads the indexed IdComp.UniqueId, rejoins the common DataIndex.Type route, and can conditionally reach RegisterEntity. RegisterEntity forwards the grid to typed state and area entity controllers, whose GetValidIndexGroup methods select the corresponding RootComp.VisibleDesc group. Base Register loops over group Num/Index and reads four-byte values from PrimitiveIntList using the grid vector slot; this selection does not rely on the stored group Type value.",
            "structuralOnly": "The current exported serialized DynamicSceneTemplates object joins the native asset path through the asset map and manifest. Every observed RootComp group's ordered DataIndex.Type signature equals its authored template comps list, so stored Comps.Num equals the matched template list length. All groups partition the grid directory. Both nested visible groups carry PrimitiveInt DataIndex spans bounded by the containing grid's PrimitiveIntList, without overlap; other PrimitiveIntList elements remain unassigned by these two groups.",
            "unresolved": "Actual resource load, live grid selection and lifecycle execution, component activation, and the meaning of selected PrimitiveIntList values are not observed.",
        },
    }


def _markdown(report: dict[str, Any]) -> str:
    corpus = report["corpus"]
    return "\n".join([
        "# DynamicStreaming RootComp group audit", "",
        f"- Status: `{report['status']}`; input set: `{report['inputSetSha256']}`.",
        f"- Authenticated main files: {corpus['files']:,}; grids: {corpus['grids']:,}; RootComp groups: {corpus['groups']:,}.",
        f"- Group spans cover {corpus['coveredDirectoryEntries']:,} DataIndex directory entries exactly.",
        f"- RootComp.Type is consumed as an EDynamicSceneEntityType template map key; all {len(report['entityTypes']):,} observed types match the current DynamicSceneTemplates asset in component order.",
        f"- Template rows: {report['template']['templateRows']:,}; rows not observed in current main grids: {len(report['template']['templateOnlyTypes']):,}.",
        f"- IdComp detour: {report['idCompPath']['directoryEntries']:,} authored rows read IdComp.UniqueId before the common route on the selected unpatched path.",
        f"- VisibleDesc: {report['visibleDesc']['counts']['visibleStateNonempty']:,} nonempty state groups and {report['visibleDesc']['counts']['visibleAreaNonempty']:,} nonempty area groups address the grid's PrimitiveIntList without overlap; {report['visibleDesc']['counts']['visibleUnreferencedInts']:,} integers have other or unresolved ownership.",
        "- Selected entity visibility controllers choose those two groups. Base Register reads each indexed integer through the PrimitiveIntList grid vector slot; group Type is not used for that vector selection.",
        "- Selected grid load/reload handlers loop over RootComp positions, call _ParseLoad, and can reach RegisterEntity through a conditional path.",
        "- The inner loop bound comes from SafeCount<EDynamicSceneData> on template comps. Its length matches stored Comps.Num across this authored corpus; live execution remains unobserved.", "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--outer-report", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)
    try:
        layout, index_layout, main_layout, enum_by_id, entity_enum, digests, receipt = validate_native_layout(
            args.gameassembly, args.metadata,
        )
        templates, template_provenance = load_current_template_asset(
            layout["templateLookup"], game_root=args.game_root, export_root=args.export_root,
            entity_enum=entity_enum, data_enum=enum_by_id,
        )
        report = audit_current_main(
            layout, index_layout, main_layout, enum_by_id, entity_enum,
            outer_path=args.outer_report, ledger_path=args.ledger, cli_path=args.cli,
            input_root=args.input_root, expected_input_set_sha256=args.expected_input_set_sha256,
            templates=templates, template_provenance=template_provenance,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as exc:
        print(f"dynamic-root-comp-native-audit: {exc}", file=sys.stderr)
        return 1
    report.update(digests)
    report["nativeInputs"] = receipt
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(
        "DynamicStreaming RootComp audit passed: "
        f"files={report['corpus']['files']} grids={report['corpus']['grids']} "
        f"groups={report['corpus']['groups']} directoryEntries={report['corpus']['coveredDirectoryEntries']}"
    )
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
