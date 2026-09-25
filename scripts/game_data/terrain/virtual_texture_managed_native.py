"""Validate the selected managed Terrain texture-resource constructor copies."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import unresolved_usage_index, usage_method_spec
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.terrain-virtual-texture-managed-native-contract.v4"
DEFAULT_CONTRACT = CONTRACTS_DIR / "terrain_virtual_texture_managed_native.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/terrain/virtual_texture_managed_native.json"


def _number(value: Any) -> int:
    return int(str(value), 0)


def _expect(image: NativeImage, rva: int, expected: bytes, label: str,
            bounds: tuple[int, int]) -> None:
    if not bounds[0] <= rva <= bounds[1] - len(expected):
        raise ValueError(f"{label}:outside-constructor-window")
    actual = image.pe.bytes_at_va(image.pe.image_base + rva, len(expected))
    if actual != expected:
        raise ValueError(f"{label}:expected={expected.hex().upper()},actual={actual.hex().upper()}")


def _call(image: NativeImage, rva: int, target: int, label: str,
          bounds: tuple[int, int]) -> None:
    if not bounds[0] <= rva <= bounds[1] - 5:
        raise ValueError(f"{label}:outside-constructor-window")
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != target:
        raise ValueError(f"{label}:direct-call-target")


def _null_exit(image: NativeImage, rva: int, target: int, label: str,
               bounds: tuple[int, int]) -> None:
    if not bounds[0] <= rva <= bounds[1] - 6:
        raise ValueError(f"{label}:outside-constructor-window")
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 6)
    if raw[:2] != b"\x0f\x84" or rva + 6 + struct.unpack_from("<i", raw, 2)[0] != target:
        raise ValueError(f"{label}:null-exit-target")


def _field(image: NativeImage, type_row: dict[str, Any], name: str,
           offset: int, expected_type: str) -> None:
    index = type_row["index"]
    if not isinstance(index, int) or image.type_name(index) != type_row["name"]:
        raise ValueError(f"type:{type_row['name']}:identity")
    fields = runtime_type_field_offsets(image.metadata, image.pe, image.registration, index)
    if fields.get(name) != offset:
        raise ValueError(f"field:{type_row['name']}.{name}:offset")
    definition = image.metadata.types[index]
    matches = [field for field in image.metadata.fields_for(definition)
               if image.metadata.string(field.name_index) == name]
    if len(matches) != 1:
        raise ValueError(f"field:{type_row['name']}.{name}:identity")
    field_type_index = matches[0].type_index
    types_va = int(image.registration["types"], 16)
    type_va = image.pe.u64_at_va(types_va + field_type_index * 8)
    actual_type = runtime_type_name(image.pe, image.metadata, type_va)
    if actual_type != expected_type:
        raise ValueError(f"field:{type_row['name']}.{name}:type={actual_type}")


def _property_field_load(prefix: bytes, offset: int) -> bytes:
    """The selected x64 [rax+offset] operand used for a property-ID word."""
    if offset == 0:
        return prefix + b"\x00"
    if 0 < offset <= 0x7F:
        return prefix + b"\x40" + bytes([offset])
    return prefix + b"\x80" + struct.pack("<i", offset)


def verify_virtual_texture_copies(image: NativeImage,
                                  contract: dict[str, Any]) -> list[dict[str, str]]:
    """Check metadata identities and the constructor's eight guarded assignments."""
    types = contract["types"]
    constructor = contract["constructor"]
    terrain = types["terrainResource"]
    resources = types["runtimeResources"]
    texture = types["textureResources"]
    renderer = types["renderer"]
    for row in types.values():
        if image.type_name(row["index"]) != row["name"]:
            raise ValueError(f"type:{row['name']}:identity")
    if not image.metadata.types[terrain["index"]].bitfield & 1:
        raise ValueError("terrainResource:expected-value-type")
    _field(image, terrain, terrain["field"], _number(terrain["fieldOffset"]),
           terrain["fieldType"])
    _field(image, resources, resources["field"], _number(resources["fieldOffset"]),
           resources["fieldType"])
    method = image.metadata.methods[constructor["methodIndex"]]
    if (image.type_name(method.declaring_type) != constructor["type"]
            or image.metadata.string(method.name_index) != constructor["method"]
            or image.method_pointer_va(method) != image.pe.image_base + _number(constructor["rva"])):
        raise ValueError("constructor:method-identity-or-pointer")
    params = image.metadata.parameters_for(method)
    if len(params) != 1 or params[0].type_index != constructor["parameterTypeIndex"]:
        raise ValueError("constructor:parameter-index")
    types_va = int(image.registration["types"], 16)
    parameter_va = image.pe.u64_at_va(types_va + params[0].type_index * 8)
    if runtime_type_name(image.pe, image.metadata, parameter_va) != constructor["parameterType"]:
        raise ValueError("constructor:parameter-type")
    bounds = (_number(constructor["windowStartRva"]), _number(constructor["windowEndRva"]))
    if bounds[0] != _number(constructor["rva"]) or bounds[1] <= bounds[0]:
        raise ValueError("constructor:window-bounds")
    window = image.pe.bytes_at_va(image.pe.image_base + bounds[0], bounds[1] - bounds[0])
    if hashlib.sha256(window).hexdigest().upper() != constructor["windowSha256"].upper():
        raise ValueError("constructor:window-sha256")
    _expect(image, _number(constructor["resourceArgumentLoadRva"]), b"\x48\x8b\x32",
            "constructor:TerrainResource.runtimeResources", bounds)
    _expect(image, _number(constructor["resourceNullTestRva"]), b"\x48\x85\xf6",
            "constructor:runtime-resources-null-test", bounds)
    _null_exit(image, _number(constructor["resourceNullBranchRva"]),
               _number(constructor["nullExitRva"]),
               "constructor:runtime-resources-null-exit", bounds)
    rows = contract["fieldCopies"]
    if len(rows) != 8 or len({row["source"] for row in rows}) != 8 or len({row["destination"] for row in rows}) != 8:
        raise ValueError("fieldCopies:expected-eight-distinct-fields")
    result: list[dict[str, str]] = []
    previous_call = _number(constructor["resourceArgumentLoadRva"])
    for row in rows:
        source_offset = _number(row["sourceOffset"])
        destination_offset = _number(row["destinationOffset"])
        if source_offset > 0x7F or destination_offset > 0x7F:
            raise ValueError(f"fieldCopy:{row['source']}:unsupported-offset-shape")
        _field(image, texture, row["source"], source_offset, row["sourceType"])
        _field(image, renderer, row["destination"], destination_offset, row["sourceType"])
        node = _number(row["sourceNodeRva"])
        read = _number(row["sourceReadRva"])
        address = _number(row["destinationAddressRva"])
        write = _number(row["destinationWriteRva"])
        call = _number(row["writeBarrierCallRva"])
        if not previous_call < node < read < address < write < call:
            raise ValueError(f"fieldCopy:{row['source']}:instruction-order")
        _expect(image, node, b"\x48\x8b\x86" + struct.pack("<i", _number(resources["fieldOffset"])),
                f"fieldCopy:{row['source']}:textures-pointer", bounds)
        _expect(image, node + 7, b"\x48\x85\xc0", f"fieldCopy:{row['source']}:null-test", bounds)
        _null_exit(image, node + 10, _number(constructor["nullExitRva"]),
                   f"fieldCopy:{row['source']}:null-exit", bounds)
        _expect(image, read, b"\x48\x8b\x40" + bytes((source_offset,)),
                f"fieldCopy:{row['source']}:source", bounds)
        _expect(image, address, b"\x48\x8d\x4f" + bytes((destination_offset,)),
                f"fieldCopy:{row['source']}:destination-address", bounds)
        _expect(image, write, b"\x48\x89\x47" + bytes((destination_offset,)),
                f"fieldCopy:{row['source']}:destination-write", bounds)
        _call(image, call, _number(constructor["writeBarrierTargetRva"]),
              f"fieldCopy:{row['source']}:write-barrier", bounds)
        previous_call = call
        result.append({"source": row["source"], "sourceType": row["sourceType"],
                       "destination": row["destination"]})
    return result


def verify_parent_renderer_handoff(image: NativeImage,
                                   contract: dict[str, Any]) -> dict[str, str]:
    """Check the parent renderer passes its TerrainResource value to the child."""
    terrain = contract["types"]["terrainResource"]
    child = contract["types"]["renderer"]
    parent = contract["types"]["parentRenderer"]
    spec = contract["parentConstructor"]
    method = image.metadata.methods[spec["methodIndex"]]
    if (image.type_name(method.declaring_type) != spec["type"]
            or image.metadata.string(method.name_index) != spec["method"]
            or image.method_pointer_va(method) != image.pe.image_base + _number(spec["rva"])):
        raise ValueError("parentConstructor:method-identity-or-pointer")
    params = image.metadata.parameters_for(method)
    if len(params) != 1 or params[0].type_index != spec["parameterTypeIndex"]:
        raise ValueError("parentConstructor:parameter-index")
    types_va = int(image.registration["types"], 16)
    parameter_va = image.pe.u64_at_va(types_va + params[0].type_index * 8)
    if runtime_type_name(image.pe, image.metadata, parameter_va) != spec["parameterType"]:
        raise ValueError("parentConstructor:parameter-type")
    if spec["parameterType"] != terrain["name"] or spec["type"] != parent["name"]:
        raise ValueError("parentConstructor:contract-type-link")
    if image.type_name(child["index"]) != child["name"] or image.type_name(parent["index"]) != parent["name"]:
        raise ValueError("parentConstructor:type-identity")
    fields = parent["fields"]
    if [row["name"] for row in fields] != ["m_vtRenderer", "m_runtimeResources", "m_configuration"]:
        raise ValueError("parentConstructor:field-order")
    if ([_number(row["offset"]) for row in fields] != [0x10, 0x18, 0x20]
            or [row["type"] for row in fields] != [
                child["name"], contract["types"]["runtimeResources"]["name"],
                contract["types"]["configuration"]["name"]]):
        raise ValueError("parentConstructor:field-contract")
    _field(image, terrain, terrain["field"], _number(terrain["fieldOffset"]),
           terrain["fieldType"])
    _field(image, terrain, terrain["configurationField"],
           _number(terrain["configurationFieldOffset"]), terrain["configurationFieldType"])
    if (_number(terrain["fieldOffset"]) - 0x10 != 0
            or _number(terrain["configurationFieldOffset"]) - 0x10 != 8
            or terrain["configurationFieldType"] != contract["types"]["configuration"]["name"]):
        raise ValueError("parentConstructor:value-field-layout")
    for row in fields:
        _field(image, parent, row["name"], _number(row["offset"]), row["type"])
    bounds = (_number(spec["windowStartRva"]), _number(spec["windowEndRva"]))
    if bounds[0] != _number(spec["rva"]) or bounds[1] <= bounds[0]:
        raise ValueError("parentConstructor:window-bounds")
    window = image.pe.bytes_at_va(image.pe.image_base + bounds[0], bounds[1] - bounds[0])
    if hashlib.sha256(window).hexdigest().upper() != spec["windowSha256"].upper():
        raise ValueError("parentConstructor:window-sha256")
    load = _number(spec["childAllocationTypeLoadRva"])
    if not bounds[0] <= load <= bounds[1] - 7:
        raise ValueError("parentConstructor:child-allocation-type-load-bounds")
    raw_load = image.pe.bytes_at_va(image.pe.image_base + load, 7)
    cell = load + 7 + struct.unpack_from("<i", raw_load, 3)[0]
    if raw_load[:3] != b"\x48\x8b\x0d" or cell != _number(spec["childAllocationTypeUsageCellRva"]):
        raise ValueError("parentConstructor:child-allocation-type-load")
    usage = image.pe.bytes_at_va(image.pe.image_base + cell, 8)
    if usage.hex().upper() != spec["childAllocationTypeUsageRawHex"].upper():
        raise ValueError("parentConstructor:child-allocation-type-usage")
    type_index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1,
        source=str(image.gameassembly), offset=cell)
    if type_index != spec["childAllocationTypeIndex"]:
        raise ValueError("parentConstructor:child-allocation-type-index")
    type_va = image.pe.u64_at_va(types_va + type_index * 8)
    if runtime_type_name(image.pe, image.metadata, type_va) != child["name"]:
        raise ValueError("parentConstructor:child-allocation-type-name")
    _expect(image, _number(spec["resourceArgumentStageRva"]), b"\x48\x8b\xda",
            "parentConstructor:terrain-resource-stage", bounds)
    _call(image, _number(spec["childAllocationCallRva"]),
          _number(spec["childAllocationTargetRva"]), "parentConstructor:child-allocation", bounds)
    _expect(image, _number(spec["childAllocationNullBranchRva"]) - 3, b"\x48\x85\xc0",
            "parentConstructor:child-allocation-null-test", bounds)
    _null_exit(image, _number(spec["childAllocationNullBranchRva"]),
               _number(spec["childAllocationNullExitRva"]),
               "parentConstructor:child-allocation-null-exit", bounds)
    _expect(image, _number(spec["resourceForwardRva"]), b"\x48\x8b\xd3",
            "parentConstructor:terrain-resource-forward", bounds)
    _expect(image, _number(spec["childArgumentForwardRva"]), b"\x48\x8b\xc8",
            "parentConstructor:child-this-forward", bounds)
    _call(image, _number(spec["childConstructorCallRva"]),
          _number(contract["constructor"]["rva"]), "parentConstructor:child-constructor", bounds)
    _expect(image, _number(spec["childFieldAddressRva"]), b"\x48\x8d\x4f\x10",
            "parentConstructor:child-field-address", bounds)
    _expect(image, _number(spec["childFieldStoreRva"]), b"\x48\x89\x77\x10",
            "parentConstructor:child-field-store", bounds)
    _call(image, _number(spec["childWriteBarrierCallRva"]),
          _number(contract["constructor"]["writeBarrierTargetRva"]),
          "parentConstructor:child-write-barrier", bounds)
    _expect(image, _number(spec["runtimeResourcesSourceRva"]), b"\x0f\x10\x13",
            "parentConstructor:runtime-resources-source", bounds)
    _expect(image, _number(spec["runtimeResourcesStoreRva"]), b"\x66\x48\x0f\xd6\x57\x18",
            "parentConstructor:runtime-resources-store", bounds)
    _call(image, _number(spec["runtimeResourcesWriteBarrierCallRva"]),
          _number(contract["constructor"]["writeBarrierTargetRva"]),
          "parentConstructor:runtime-resources-write-barrier", bounds)
    _expect(image, _number(spec["configurationSourceRva"]), b"\xf3\x0f\x7e\x53\x08",
            "parentConstructor:configuration-source", bounds)
    _expect(image, _number(spec["configurationStoreRva"]), b"\x66\x48\x0f\xd6\x57\x20",
            "parentConstructor:configuration-store", bounds)
    _call(image, _number(spec["configurationWriteBarrierCallRva"]),
          _number(contract["constructor"]["writeBarrierTargetRva"]),
          "parentConstructor:configuration-write-barrier", bounds)
    ordered = [spec[key] for key in (
        "resourceArgumentStageRva", "childAllocationCallRva", "childAllocationNullBranchRva",
        "resourceForwardRva", "childArgumentForwardRva", "childConstructorCallRva",
        "childFieldAddressRva", "childFieldStoreRva", "childWriteBarrierCallRva",
        "runtimeResourcesSourceRva", "runtimeResourcesStoreRva",
        "runtimeResourcesWriteBarrierCallRva", "configurationSourceRva",
        "configurationStoreRva", "configurationWriteBarrierCallRva")]
    if list(map(_number, ordered)) != sorted(map(_number, ordered)):
        raise ValueError("parentConstructor:instruction-order")
    return {"parent": parent["name"], "child": child["name"],
            "argument": terrain["name"], "runtimeResourcesField": fields[1]["name"]}


def direct_relative_call_candidates(pe: Any, target_rva: int) -> list[dict[str, str]]:
    """Find E8/rel32 byte candidates across every raw-backed PE section.

    This is a complete byte census for this one encoding, not a proof about
    indirect calls, patched dispatch, or runtime use. A nonempty candidate
    still needs instruction-boundary and caller-flow validation.
    """
    rows: list[dict[str, str]] = []
    raw = pe.buf
    for section in pe.sections:
        start = section["rawPointer"]
        end = min(len(raw), start + section["rawSize"])
        offset = start
        while True:
            offset = raw.find(b"\xe8", offset, end - 4)
            if offset < 0:
                break
            source_rva = section["virtualAddress"] + offset - start
            destination = source_rva + 5 + struct.unpack_from("<i", raw, offset + 1)[0]
            if destination == target_rva:
                rows.append({"section": section["name"], "sourceRva": hex(source_rva)})
            offset += 1
    return rows


def verify_conversion_route(image: NativeImage,
                            contract: dict[str, Any]) -> list[dict[str, str]]:
    """Check the selected converter's direct setup handoff by named methods."""
    result: list[dict[str, str]] = []
    route = contract["conversionRoute"]
    if len(route) != 3:
        raise ValueError("terrain-conversion:expected-three-edges")
    for position, row in enumerate(route):
        source, target = row["source"], row["target"]
        if position and source != route[position - 1]["target"]:
            raise ValueError("terrain-conversion:disconnected-route")
        source_rva, target_rva = _number(source["rva"]), _number(target["rva"])
        image.validate_method_row(
            [source["methodIndex"], source["type"], source["method"], source_rva],
            label="terrain-conversion-source")
        if "parameters" in source:
            method = image.metadata.methods[source["methodIndex"]]
            types_va = int(image.registration["types"], 16)
            actual = [runtime_type_name(
                image.pe, image.metadata,
                image.pe.u64_at_va(types_va + parameter.type_index * 8))
                for parameter in image.metadata.parameters_for(method)]
            if actual != source["parameters"]:
                raise ValueError("terrain-conversion:source-parameters")
        image.validate_method_row(
            [target["methodIndex"], target["type"], target["method"], target_rva],
            label="terrain-conversion-target")
        call_rva = _number(row["callRva"])
        _call(image, call_rva, target_rva, "terrain-conversion:direct-call",
              (source_rva, _number(row["sourceWindowEndRva"])))
        result.append({"source": f"{source['type']}.{source['method']}",
                       "target": f"{target['type']}.{target['method']}",
                       "callRva": row["callRva"]})
    return result


def verify_phase1_property_arguments(image: NativeImage,
                                     contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Check four converter property IDs and their local-to-Phase1 argument flow."""
    spec = contract["phase1PropertyArguments"]
    bounds = (_number(spec["windowStartRva"]), _number(spec["windowEndRva"]))
    source = contract["conversionRoute"][0]["source"]
    if not (_number(source["rva"]) <= bounds[0] < bounds[1]
            <= _number(contract["conversionRoute"][0]["sourceWindowEndRva"])):
        raise ValueError("phase1-properties:window-bounds")
    window = image.pe.bytes_at_va(image.pe.image_base + bounds[0], bounds[1] - bounds[0])
    if hashlib.sha256(window).hexdigest().upper() != spec["windowSha256"].upper():
        raise ValueError("phase1-properties:window-sha256")

    owner = spec["staticType"]
    if image.type_name(owner["index"]) != owner["name"] or owner["index"] != image.metadata.methods[source["methodIndex"]].declaring_type:
        raise ValueError("phase1-properties:static-type-identity")
    cell_rva = _number(owner["usageCellRva"])
    usage = image.pe.bytes_at_va(image.pe.image_base + cell_rva, 8)
    if usage.hex().upper() != owner["usageRawHex"].upper():
        raise ValueError("phase1-properties:static-type-usage-bytes")
    usage_index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1,
        source=str(image.gameassembly), offset=cell_rva)
    if usage_index != owner["registeredTypeIndex"]:
        raise ValueError("phase1-properties:static-type-usage-index")
    types_va = int(image.registration["types"], 16)
    if runtime_type_name(image.pe, image.metadata,
                         image.pe.u64_at_va(types_va + usage_index * 8)) != owner["name"]:
        raise ValueError("phase1-properties:static-type-usage-name")

    phase = contract["conversionRoute"][0]["target"]
    phase_method = image.metadata.methods[phase["methodIndex"]]
    actual_types = [runtime_type_name(
        image.pe, image.metadata, image.pe.u64_at_va(types_va + param.type_index * 8))
        for param in image.metadata.parameters_for(phase_method)]
    if actual_types != spec["phase1ParameterTypes"] or len(actual_types) < 5:
        raise ValueError("phase1-properties:phase1-parameter-types")

    helper = spec["helperMethod"]
    helper_method = image.metadata.methods[helper["methodIndex"]]
    if (image.type_name(helper_method.declaring_type) != helper["type"]
            or image.metadata.string(helper_method.name_index) != helper["name"]):
        raise ValueError("phase1-properties:helper-method-identity")
    specs_va = int(image.registration["methodSpecs"], 16)
    spec_records = image.pe.bytes_at_va(
        specs_va, image.registration["methodSpecsCount"] * 12)

    rows = spec["requests"]
    if len(rows) != 4 or len({row["property"] for row in rows}) != 4 or len({row["resultSlot"] for row in rows}) != 4:
        raise ValueError("phase1-properties:four-distinct-requests")
    arg_registers = {1: "r8", 2: "r9", 3: "stack+0x20", 4: "stack+0x28"}
    arg_load_prefix = {"r8": b"\x4c\x8b\x84\x24", "r9": b"\x4c\x8b\x8c\x24",
                       "stack+0x20": b"\x48\x8b\x84\x24", "stack+0x28": b"\x48\x8b\x84\x24"}
    result = []
    previous_call = bounds[0]
    for row in rows:
        name = row["property"]
        field_offset = _number(row["fieldOffset"])
        _field(image, owner, name, field_offset, spec["propertyType"])
        expected_head = _property_field_load(b"\xf2\x0f\x10", field_offset)
        expected_tail = _property_field_load(b"\x8b", field_offset + 8)
        if (bytes.fromhex(row["idHeadHex"]) != expected_head
                or bytes.fromhex(row["idTailHex"]) != expected_tail):
            raise ValueError(f"phase1-properties:{name}:field-load-contract")
        slot = _number(row["resultSlot"])
        index = row["phase1ParameterIndex"]
        argument = row["phase1Argument"]
        if arg_registers.get(index) != argument or not 0 <= slot <= 0x10000:
            raise ValueError(f"phase1-properties:{name}:argument-contract")
        load = _number(row["classLoadRva"])
        static = _number(row["staticFieldsLoadRva"])
        head, tail = _number(row["idHeadRva"]), _number(row["idTailRva"])
        method_load = _number(row["methodSpecLoadRva"])
        output, call = _number(row["resultAddressRva"]), _number(row["helperCallRva"])
        phase_load = _number(row["phase1LoadRva"])
        if not previous_call <= load < static < head < tail < method_load < output < call < phase_load < bounds[1]:
            raise ValueError(f"phase1-properties:{name}:instruction-order")
        raw_load = image.pe.bytes_at_va(image.pe.image_base + load, 7)
        if (raw_load[:3] != b"\x48\x8b\x05"
                or load + 7 + struct.unpack_from("<i", raw_load, 3)[0] != cell_rva):
            raise ValueError(f"phase1-properties:{name}:static-class-load")
        _expect(image, static, b"\x48\x8b\x80" + struct.pack("<i", _number(owner["staticFieldsOffset"])),
                f"phase1-properties:{name}:static-fields", bounds)
        _expect(image, head, bytes.fromhex(row["idHeadHex"]),
                f"phase1-properties:{name}:id-head", bounds)
        _expect(image, tail, bytes.fromhex(row["idTailHex"]),
                f"phase1-properties:{name}:id-tail", bounds)
        method_raw = image.pe.bytes_at_va(image.pe.image_base + method_load, 7)
        method_cell = _number(row["methodSpecUsageCellRva"])
        if (method_raw[:3] != b"\x4c\x8b\x0d"
                or method_load + 7 + struct.unpack_from("<i", method_raw, 3)[0] != method_cell):
            raise ValueError(f"phase1-properties:{name}:method-spec-load")
        usage_raw = image.pe.bytes_at_va(image.pe.image_base + method_cell, 8)
        if usage_raw.hex().upper() != row["methodSpecUsageRawHex"].upper():
            raise ValueError(f"phase1-properties:{name}:method-spec-usage-bytes")
        method_spec = usage_method_spec(
            usage_raw, spec_records, len(image.metadata.methods),
            image.registration["genericInstsCount"],
            source=str(image.gameassembly), usage_offset=image.pe.image_base + method_cell,
            records_offset=specs_va)
        if (method_spec["index"] != row["methodSpecIndex"]
                or method_spec["rawHex"] != row["methodSpecRawHex"]
                or method_spec["definition"] != helper["methodIndex"]
                or method_spec["classInstantiationIndex"] != -1
                or method_spec["methodInstantiationIndex"] != row["methodInstantiationIndex"]):
            raise ValueError(f"phase1-properties:{name}:method-spec-identity")
        instantiation = image.instantiations.resolve(row["methodInstantiationIndex"])
        if (len(instantiation.arguments) != 1
                or runtime_type_name(image.pe, image.metadata,
                                     instantiation.arguments[0].type_pointer_va) != actual_types[index]):
            raise ValueError(f"phase1-properties:{name}:method-generic-type")
        _expect(image, output, b"\x4c\x8d\x84\x24" + struct.pack("<i", slot),
                f"phase1-properties:{name}:result-address", bounds)
        _call(image, call, _number(spec["helperTargetRva"]),
              f"phase1-properties:{name}:helper-call", bounds)
        _expect(image, phase_load, arg_load_prefix[argument] + struct.pack("<i", slot),
                f"phase1-properties:{name}:phase1-local-load", bounds)
        if argument.startswith("stack+"):
            destination = _number(argument.split("+", 1)[1])
            _expect(image, _number(row["phase1StoreRva"]),
                    b"\x48\x89\x44\x24" + bytes([destination]),
                    f"phase1-properties:{name}:phase1-stack-store", bounds)
        elif "phase1StoreRva" in row:
            raise ValueError(f"phase1-properties:{name}:unexpected-stack-store")
        previous_call = call
        result.append({"property": name, "conversionMethod": f"{helper['type']}.{helper['name']}",
                       "phase1ParameterIndex": index,
                       "phase1ParameterType": actual_types[index], "resultSlot": row["resultSlot"]})
    if {row["phase1ParameterIndex"] for row in result} != set(arg_registers):
        raise ValueError("phase1-properties:phase1-argument-coverage")
    _call(image, _number(contract["conversionRoute"][0]["callRva"]),
          _number(phase["rva"]), "phase1-properties:phase1-call", bounds)
    return result


def validate_terrain_virtual_texture_managed(*, game_root: Path,
                                             contract_path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    """Authenticate one installed build; withhold all copied-field claims on drift."""
    try:
        contract, _ = read_reviewed_contract(
            contract_path, schema=SCHEMA, status="validated", label="terrain-virtual-texture-managed"
        )
        expected = contract["nativeInputs"]
        if not isinstance(expected, dict):
            raise ValueError("nativeInputs:not-object")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        return {"status": "validation_failed", "fieldCopies": [], "parentHandoff": None,
                "conversionRoute": [], "phase1PropertyArguments": [],
                "directRelativeCallCandidates": {},
                "reason": f"contract={error}"}
    root = Path(game_root)
    gate = check_installed_native_inputs(
        str(expected.get("gameAssemblySha256") or ""),
        str(expected.get("metadataSha256") or ""),
        gameassembly=root.parent / "GameAssembly.dll",
        metadata=root / "il2cpp_data/Metadata/global-metadata.dat",
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return {"status": gate.status, "fieldCopies": [], "parentHandoff": None,
                "conversionRoute": [], "phase1PropertyArguments": [],
                "directRelativeCallCandidates": {},
                "reason": gate.detail}
    try:
        unity_hash = sha256_file_upper(root.parent / "UnityPlayer.dll")
    except OSError as error:
        return {"status": "missing", "fieldCopies": [], "parentHandoff": None,
                "conversionRoute": [], "phase1PropertyArguments": [],
                "directRelativeCallCandidates": {},
                "reason": f"UnityPlayer.dll={error}"}
    if unity_hash != str(expected.get("unityPlayerSha256") or "").upper():
        return {"status": "mismatched", "fieldCopies": [], "parentHandoff": None,
                "conversionRoute": [], "phase1PropertyArguments": [],
                "directRelativeCallCandidates": {},
                "reason": "UnityPlayer.dll hash differs"}
    try:
        image = NativeImage(root.parent / "GameAssembly.dll",
                            root / "il2cpp_data/Metadata/global-metadata.dat",
                            label="terrain-virtual-texture-managed")
        copies = verify_virtual_texture_copies(image, contract)
        handoff = verify_parent_renderer_handoff(image, contract)
        conversion_route = verify_conversion_route(image, contract)
        phase1_arguments = verify_phase1_property_arguments(image, contract)
        calls = {
            "parentConstructor": direct_relative_call_candidates(
                image.pe, _number(contract["parentConstructor"]["rva"])),
            "childConstructor": direct_relative_call_candidates(
                image.pe, _number(contract["constructor"]["rva"])),
        }
        child_call = hex(_number(contract["parentConstructor"]["childConstructorCallRva"]))
        if {row["sourceRva"] for row in calls["childConstructor"]} != {child_call}:
            raise ValueError("direct-relative-call-census:child-call-candidate-differs")
    except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error, RuntimeError) as error:
        return {"status": "validation_failed", "fieldCopies": [], "parentHandoff": None,
                "conversionRoute": [], "phase1PropertyArguments": [],
                "directRelativeCallCandidates": {},
                "reason": str(error)}
    return {"status": "validated", "fieldCopies": copies, "parentHandoff": handoff,
            "conversionRoute": conversion_route, "phase1PropertyArguments": phase1_arguments,
            "directRelativeCallCandidates": calls,
            "nativeInputs": expected, "evidenceBoundary": contract["evidenceBoundary"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True,
                        help="Explicit selected Endfield_Data root")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if (REPO_ROOT / "reports").resolve() not in output.parents:
        parser.error("--output must be under reports/")
    result = validate_terrain_virtual_texture_managed(
        game_root=args.game_root, contract_path=args.contract
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Terrain managed texture copies: {result['status']}; "
          f"{len(result['fieldCopies'])} fields, {len(result['conversionRoute'])} conversion calls, "
          f"{len(result['phase1PropertyArguments'])} phase1 property arguments")
    if result["status"] != "validated":
        print(result.get("reason", ""))
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
