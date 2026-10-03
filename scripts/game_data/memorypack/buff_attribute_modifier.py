"""Native-gated shared AttributeModifierData storage, independent of source IDs.

The reviewed root context owns the collection type, and its array context owns
AttributeModifier elements. The nullable array, nullable element wrappers and
nullable BlackboardDouble params are distinct states; the terminal collection
byte remains required after an empty or null array. This is stored structure,
not attribute evaluation or a live formatter-provider observation.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.memorypack import buff_adding_cooldown as blackboard
from scripts.game_data.memorypack.buff_actions import Reader

LABEL = "buffAttributeModifier"
SCHEMA = "endfield.buff-attribute-modifier-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_attribute_modifier_native.json"
PREFIX_PATH = CONTRACTS_DIR / "buff_root_prefix_native.json"
ATTRIBUTE_PATH = CONTRACTS_DIR / "buff_heal_processor_zero_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA,
        status="exact-current-build", label=LABEL)
    if (contract.get("reviewedDependencies") != [PREFIX_PATH.name, ATTRIBUTE_PATH.name,
            blackboard.CONTRACT_PATH.name]
            or len(contract.get("attributeCollectionSetters") or []) != 2):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def _selected_type(image: Any, name: str) -> Any:
    owners = [row for row in image.metadata.types
              if image.metadata.type_full_name(row) == name]
    if len(owners) != 1:
        raise ValueError(f"{LABEL}.native:type={name}; matches={len(owners)}")
    return owners[0]


def _validate_attribute_native(
    contract: dict[str, Any], prefix: dict[str, Any], heal: dict[str, Any],
    *, gameassembly: Path, metadata: Path,
) -> dict[str, Any]:
    """Authenticate the shared collection and element bodies without selecting a file."""
    if (prefix.get("schemaVersion") != 1
            or prefix["methods"][5] != heal["methods"][3]
            or len(prefix.get("codeWindows") or []) < 11
            or len(heal.get("wrapperSetters", {}).get("attributeModifier", [])) != 4
            or len(heal.get("attributeValueStores") or []) != 4):
        raise ValueError(f"{LABEL}.native:attribute-dependency-shape")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["GameAssembly.dll"], inputs["global-metadata.dat"],
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail}
    image = open_native_image(gate.gameassembly, gate.metadata)
    for row in prefix["methods"][2:6]:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(prefix["codeWindows"][4:11] + [heal["codeWindows"][3]],
                        label=LABEL)
    # Independently rejoin both enclosing type contexts. The array helper's
    # complete reviewed body owns signed count/null and repeated element reads;
    # neither an observed array length nor a fitting element picks the type.
    for row in (prefix["nestedContexts"][3], prefix["nestedContexts"][5]):
        cell, usage = image.nested_usage_cell(row, label=LABEL)
        index = method_spec_usage_index(usage, image.registration["methodSpecsCount"],
                                        source=LABEL, offset=cell)
        spec = list(struct.unpack("<iii", image.pe.bytes_at_va(
            int(image.registration["methodSpecs"], 16) + index * 12, 12)))
        args = image.instantiations.resolve(spec[2]).arguments
        if (index != row["methodSpecIndex"] or spec != row["methodSpec"]
                or len(args) != 1 or args[0].raw_type_record_hex != row["argumentRawHex"]
                or image.type_name(row["typeDefinition"]) != row["typeName"]):
            raise ValueError(f"{LABEL}.native:enclosing-type-context")
    collection_owner = prefix["methods"][3][1]
    collection_setters = contract["attributeCollectionSetters"]
    if image.setter_methods(_selected_type(image, collection_owner),
                            parameter="typeName", label=LABEL) != [row[:3] for row in collection_setters]:
        raise ValueError(f"{LABEL}.native:attribute-collection-setters")
    for row in collection_setters:
        image.validate_method_row([row[0], collection_owner, row[1], row[3]], label=LABEL)
    item_owner = prefix["methods"][5][1]
    item_setters = heal["wrapperSetters"]["attributeModifier"]
    if image.setter_methods(_selected_type(image, item_owner),
                            parameter="typeName", label=LABEL) != [row[:3] for row in item_setters]:
        raise ValueError(f"{LABEL}.native:attribute-item-setters")
    for row in item_setters:
        image.validate_method_row([row[0], item_owner, row[1], row[3]], label=LABEL)
    names = [row[1].removeprefix("set___").removesuffix("__") for row in item_setters]
    calls = heal["sourceCalls"]["attributeModifier"]
    contexts = [row for row in heal["genericContexts"] if row["role"] in names]
    if ([row["role"] for row in calls] != [f"{name}-read" for name in names]
            or [row["role"] for row in contexts] != names):
        raise ValueError(f"{LABEL}.native:attribute-read-order")
    for row in calls:
        rva = row["instructionRva"]
        raw = bytes.fromhex(row["rawHex"])
        if (len(raw) != 5 or raw[0] != 0xE8
                or image.pe.bytes_at_va(image.pe.image_base + rva, 5) != raw
                or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != row["targetRva"]):
            raise ValueError(f"{LABEL}.native:attribute-read={row['role']}")
    for row, setter in zip(contexts, item_setters):
        cell, usage = image.nested_usage_cell(row, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
        )
        spec = list(struct.unpack("<iii", image.pe.bytes_at_va(
            int(image.registration["methodSpecs"], 16) + index * 12, 12,
        )))
        args = image.instantiations.resolve(spec[2]).arguments
        if (index != row["methodSpecIndex"] or spec != row["methodSpec"]
                or len(args) != 1 or args[0].raw_type_record_hex != row["argumentRawHex"]
                or image.type_name(struct.unpack_from(
                    "<I", bytes.fromhex(row["argumentRawHex"]))[0]) != row["typeName"]
                or row["typeName"] != setter[2]):
            raise ValueError(f"{LABEL}.native:attribute-context={row['role']}")
    value_owner = _selected_type(image, heal["wrapperSetters"]["processorZero"][0][2])
    offsets = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, value_owner.index,
    )
    if offsets != heal["attributeValueFieldOffsets"]:
        raise ValueError(f"{LABEL}.native:attribute-field-offsets")
    for rva, raw_hex, role in heal["attributeValueStores"]:
        raw = bytes.fromhex(raw_hex)
        expected = b"\x48\x89\x41" if role == "param" else b"\x89\x41"
        if (image.pe.bytes_at_va(image.pe.image_base + rva, len(raw)) != raw
                or raw[:-1] != expected or raw[-1] != offsets[role]):
            raise ValueError(f"{LABEL}.native:attribute-store={role}")
    return {"status": "validated", "collectionReadOrder": [
        row[1].removeprefix("set___").removesuffix("__")
        for row in collection_setters], "itemReadOrder": names}


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict[str, Any]:
    contract = _contract()
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(inputs["GameAssembly.dll"], inputs["global-metadata.dat"],
                                        gameassembly=gameassembly, metadata=metadata)
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail}
    prefix = json.loads(PREFIX_PATH.read_bytes())
    heal, _ = read_reviewed_contract(ATTRIBUTE_PATH,
        schema="endfield.buff-heal-processor-zero-native-contract.v1",
        status="exact-current-build", label=LABEL)
    if heal.get("nativeInputs") != inputs:
        raise ValueError(f"{LABEL}.native:dependency-input-drift")
    blackboard_contract, _ = read_reviewed_contract(blackboard.CONTRACT_PATH,
        schema="endfield.buff-adding-cooldown-ownership-native-contract.v1",
        status="exact-current-build", label=LABEL)
    if blackboard_contract.get("nativeInputs") != inputs:
        raise ValueError(f"{LABEL}.native:blackboard-input-drift")
    native = _validate_attribute_native(contract, prefix, heal,
                                        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if native.get("status") != "validated":
        return native
    child = blackboard.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata)
    if child.get("status") != "validated":
        return {"status": child.get("status", "failed"), "detail": child.get("detail"), "failedChild": "param"}
    return {**native, "nativeInputs": inputs, "blackboardChild": child,
            "evidenceBoundary": contract["evidenceBoundary"]}


def decode_attribute_modifier(data: bytes, start: int, end: int, *, source: str,
                              native_validation: dict[str, Any]) -> dict[str, Any]:
    """Reparse an owned collection and name every recursively closed item."""
    if (native_validation.get("status") != "validated"
            or native_validation.get("blackboardChild", {}).get("status") != "validated"
            or native_validation.get("collectionReadOrder") != ["attributeModifiers", "isConvertedAttribute"]
            or native_validation.get("itemReadOrder") != ["attributeType", "formulaItem", "modifyAttributeType", "param"]):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError(f"{LABEL}.boundary:invalid")
    reader = Reader(data, source, end)
    reader.pos = start
    reader.modifier_collection_profile()
    if reader.pos != end:
        raise ValueError(f"{LABEL}.cursor:expected={end}; actual={reader.pos}")
    if data[start] == 0xFF:
        return {"status": "exact-null", "startOffset": start, "consumedEnd": end,
                "memberCount": None, "fields": [], "wholeValueExact": True}
    count = struct.unpack_from("<i", data, start + 1)[0]
    items = [row for row in reader.records if row.get("kind") == "anonymous-modifier-element-profile"]
    if len(items) != max(0, count):
        raise ValueError(f"{LABEL}.array:item-count")
    children = []
    cursor = start + 5
    for index, item in enumerate(items):
        if item["start"] != cursor:
            raise ValueError(f"{LABEL}.array:noncontiguous")
        cursor = item["end"]
        fields = []
        if data[item["start"]] != 0xFF:
            position = item["start"] + 1
            for name in native_validation["itemReadOrder"][:3]:
                fields.append({"name": name, "start": position, "end": position + 4,
                               "rawBitsHex": data[position:position + 4].hex().upper()})
                position += 4
            param = blackboard.decode_adding_cooldown(data, position, item["end"],
                native_validation=native_validation["blackboardChild"])
            fields.append({"name": "param", "start": position, "end": item["end"], "child": param})
        children.append({"indexInArray": index, "start": item["start"], "end": item["end"],
                         "isNull": data[item["start"]] == 0xFF, "fields": fields, "wholeValueExact": True})
    if cursor != end - 1:
        raise ValueError(f"{LABEL}.array:terminal-endpoint")
    return {"status": "exact", "startOffset": start, "consumedEnd": end, "memberCount": 2,
            "fields": [{"name": "attributeModifiers", "start": start + 1, "end": cursor,
                        "count": count, "isNull": count == -1, "children": children},
                       {"name": "isConvertedAttribute", "start": cursor, "end": end,
                        "rawByte": data[cursor]}], "count": count, "wholeValueExact": True,
            "evidenceBoundary": "Exact stored child grammar; raw enum/flag/value bytes, no evaluated attribute or live provider."}


