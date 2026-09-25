"""Selected-build ownership and raw-byte decoder for BuffData.dispelConfig."""
from __future__ import annotations

import hashlib
import json
import struct
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "buffDispelConfig"
CONTRACT_PATH = CONTRACTS_DIR / "buff_dispel_config_native.json"
ROOT_CONTRACT_PATH = CONTRACTS_DIR / "buff_root_prefix_native.json"
SCHEMA = "endfield.buff-dispel-config-native-contract.v1"
OBJECT_HEADER_SIZE = 16


def _contract() -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL
    )
    return value


def _selected_type(image: Any, name: str) -> Any:
    matches = [row for row in image.metadata.types
               if image.metadata.type_full_name(row) == name]
    if len(matches) != 1:
        raise ValueError(f"{LABEL}.native:type={name}; matches={len(matches)}")
    return matches[0]


def _field_type_name(image: Any, field: Any) -> str:
    table = int(image.registration["types"], 16)
    pointer = image.pe.u64_at_va(table + field.type_index * 8)
    return runtime_type_name(image.pe, image.metadata, pointer)


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the eight-byte source copy and both declared child fields."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != "validated":
        return {"status": gate.status, "nativeStatus": gate.status, "detail": gate.detail,
                "evidenceBoundary": "No named child fields on missing or mismatched native inputs."}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "nativeStatus": "missing", "detail": f"{unity} is absent"}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "mismatched", "nativeStatus": "mismatched", "detail": "UnityPlayer.dll hash differs"}

    image = open_native_image(gate.gameassembly, gate.metadata)
    if image.code_registration != contract["codeRegistrationVa"]:
        raise ValueError(f"{LABEL}.native:code-registration={image.code_registration:#x}")
    if contract["reviewedDependencies"] != [ROOT_CONTRACT_PATH.name]:
        raise ValueError(f"{LABEL}.native:dependency-list")
    root = json.loads(ROOT_CONTRACT_PATH.read_text(encoding="utf-8"))
    if root.get("schemaVersion") != 1 or root["methods"][1] != contract["methods"][0]:
        raise ValueError(f"{LABEL}.native:root-dependency")
    for method in contract["methods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(root["codeWindows"][:1], label=LABEL)
    instructions = contract["sourceToFieldInstructions"]
    window = root["codeWindows"][0]
    if not (window["startRva"] <= instructions[0][0]
            and all(left[0] < right[0] for left, right in zip(instructions, instructions[1:]))
            and instructions[-1][0] + len(bytes.fromhex(instructions[-1][1])) <= window["endRva"]):
        raise ValueError(f"{LABEL}.native:source-instruction-order")
    image.check_instruction_windows(instructions, label=LABEL)

    wrapper = _selected_type(image, contract["methods"][1][1])
    setter = image.metadata.methods[contract["methods"][1][0]]
    if setter.declaring_type != wrapper.index or setter.parameter_count != 1:
        raise ValueError(f"{LABEL}.native:wrapper-setter")
    parameter = image.metadata.parameters[setter.parameter_start]
    if parameter.type_index != contract["wrapperSetterParameterTypeIndex"]:
        raise ValueError(f"{LABEL}.native:setter-parameter-index")
    if _field_type_name(image, parameter) != contract["valueType"]:
        raise ValueError(f"{LABEL}.native:setter-parameter-type")

    owner_name, _, owner_field = contract["ownerField"].partition("::")
    owner = _selected_type(image, owner_name)
    owner_field_offsets = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, owner.index
    )
    owner_offset = owner_field_offsets[owner_field]
    owner_declared = next(field for field in image.metadata.fields_for(owner)
                          if image.metadata.string(field.name_index) == owner_field)
    if _field_type_name(image, owner_declared) != contract["valueType"]:
        raise ValueError(f"{LABEL}.native:owner-field-type")
    store_bytes = bytes.fromhex(instructions[-1][1])
    if store_bytes != b"\x48\x89\x98" + struct.pack("<I", owner_offset):
        raise ValueError(f"{LABEL}.native:owner-store-offset")

    value = _selected_type(image, contract["valueType"])
    if value.index != contract["valueTypeDefinition"]:
        raise ValueError(f"{LABEL}.native:value-type-definition")
    fields = image.metadata.fields_for(value)
    if [image.metadata.string(field.name_index) for field in fields] != [
        row["name"] for row in contract["valueFields"]
    ]:
        raise ValueError(f"{LABEL}.native:value-field-order")
    offsets = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, value.index
    )
    if [offsets[row["name"]] for row in contract["valueFields"]] != [
        row["runtimeOffset"] for row in contract["valueFields"]
    ]:
        raise ValueError(f"{LABEL}.native:value-field-offsets")
    if any(row["runtimeOffset"] - OBJECT_HEADER_SIZE != row["wireOffset"]
           for row in contract["valueFields"]):
        raise ValueError(f"{LABEL}.native:value-wire-offsets")
    if [_field_type_name(image, field) for field in fields] != [
        row["type"] for row in contract["valueFields"]
    ]:
        raise ValueError(f"{LABEL}.native:value-field-types")
    size_table = int(image.registration["typeDefinitionsSizes"], 16)
    size_pointer = image.pe.u64_at_va(size_table + value.index * 8)
    boxed_size = image.pe.u32_at_va(size_pointer)
    if boxed_size != contract["valueTypeBoxedSize"] or boxed_size - OBJECT_HEADER_SIZE != contract["valueTypeRawSize"]:
        raise ValueError(f"{LABEL}.native:value-size={boxed_size}")

    enum = _selected_type(image, contract["enumType"])
    enum_underlying = next(field for field in image.metadata.fields_for(enum)
                           if image.metadata.string(field.name_index) == "value__")
    if _field_type_name(image, enum_underlying) != contract["enumUnderlyingType"]:
        raise ValueError(f"{LABEL}.native:enum-underlying")
    return {"status": "validated", "nativeStatus": "validated",
            "field": contract["ownerField"], "rawSize": contract["valueTypeRawSize"],
            "valueFields": contract["valueFields"], "nativeInputs": expected,
            "evidenceBoundary": contract["evidenceBoundary"]}


def decode_dispel_config(
    data: bytes, start: int, end: int, *, native_validation: dict[str, Any]
) -> dict[str, Any]:
    """Decode one authenticated raw-eight value; keep padding and enum raw."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError(f"{LABEL}.boundary:invalid")
    if end - start != 8:
        raise ValueError(f"{LABEL}.boundary:expected-eight actual={end - start}")
    raw_bool = data[start]
    if raw_bool not in (0, 1):
        raise ValueError(f"{LABEL}.canBeDispelled:invalid-bool={raw_bool}")
    padding = data[start + 1:start + 4]
    raw_enum = data[start + 4:end]
    level = struct.unpack("<i", raw_enum)[0]
    return {
        "status": "exact", "startOffset": start, "consumedEnd": end,
        "wholeValueExact": True, "representation": "unmanaged-struct-raw8",
        "fields": [
            {"name": "canBeDispelled", "start": start, "end": start + 1,
             "declaredType": "bool", "rawByte": raw_bool, "value": bool(raw_bool),
             "boundaryClass": "exact-cursor"},
            {"name": "dispelledLevel", "start": start + 4, "end": end,
             "declaredType": "Beyond.Gameplay.Core.DispelLevel", "rawBitsHex": raw_enum.hex().upper(),
             "rawSignedValue": level, "boundaryClass": "exact-cursor"},
        ],
        "paddingRange": [start + 1, start + 4],
        "paddingHex": padding.hex().upper(),
        "evidenceBoundary": "Stored native value layout only; no runtime dispel behavior.",
    }
