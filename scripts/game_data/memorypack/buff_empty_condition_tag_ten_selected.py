"""One selected BuffData damage modifier with an empty condition and tag ten.

The direct parent, SequenceActionData and ModifyCalcResult children already
have reviewed native contracts. This receipt joins them on one original
logical source and leaves the corpus publication gate unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.memorypack import buff_adding_cooldown as blackboard
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier
from scripts.game_data.memorypack import buff_damage_sequence_action_condition_receipt as sequence
from scripts.game_data.memorypack import buff_damage_modify_calc_result_processor_child_receipt as processor
from scripts.game_data.memorypack.buff_residual_actions import _ResidualReader
from scripts.game_data.memorypack.buff_root_no_positive_native import (
    validate_current_native_contract as validate_root_native,
)


LABEL = "buffEmptyConditionTagTenSelected"
SCHEMA = "endfield.buff-empty-condition-tag-ten-selected-native-contract.v2"
CONTRACT_PATH = CONTRACTS_DIR / "buff_empty_condition_tag_ten_selected_native.json"
ROOT_PATH = CONTRACTS_DIR / "buff_root_no_positive_native.json"
PREFIX_PATH = CONTRACTS_DIR / "buff_root_prefix_native.json"
ATTRIBUTE_PATH = CONTRACTS_DIR / "buff_heal_processor_zero_native.json"
MODIFIER_PATH = CONTRACTS_DIR / "buff_damage_modifier_child_native.json"
SEQUENCE_PATH = CONTRACTS_DIR / "buff_damage_sequence_action_condition_native.json"
PROCESSOR_PATH = CONTRACTS_DIR / "buff_damage_modify_calc_result_processor_child_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL,
    )
    selected = contract.get("selectedSource") or {}
    path = selected.get("path")
    spans = ("attributeModifier", "attributeItem", "attributeParam",
             "attributeTerminal", "damageModifier", "item", "condition", "processors",
             "processorTen", "enableSide")
    if (
        contract.get("reviewedDependencies")
        != [ROOT_PATH.name, PREFIX_PATH.name, ATTRIBUTE_PATH.name,
            MODIFIER_PATH.name, SEQUENCE_PATH.name, PROCESSOR_PATH.name]
        or not isinstance(path, str)
        or PurePosixPath(path).parts[:3] != ("Data", "Json", "BuffData")
        or len(PurePosixPath(path).parts) != 4 or not path.endswith(".json")
        or not isinstance(selected.get("sha256"), str)
        or len(selected["sha256"]) != 64
        or any(ch not in "0123456789ABCDEF" for ch in selected["sha256"])
        or type(selected.get("length")) is not int or selected["length"] <= 0
        or any(not isinstance(selected.get(key), list) or len(selected[key]) != 2
               or any(type(offset) is not int for offset in selected[key])
               or not 0 <= selected[key][0] < selected[key][1] <= selected["length"]
               for key in spans)
        or not (selected["attributeModifier"][0] < selected["attributeItem"][0]
                < selected["attributeParam"][0] < selected["attributeParam"][1]
                == selected["attributeItem"][1] == selected["attributeTerminal"][0]
                < selected["attributeTerminal"][1] == selected["attributeModifier"][1]
                < selected["damageModifier"][0] < selected["item"][0]
                < selected["condition"][0] < selected["condition"][1]
                == selected["processors"][0] < selected["processorTen"][0]
                < selected["processorTen"][1] == selected["processors"][1]
                == selected["enableSide"][0] < selected["enableSide"][1]
                == selected["item"][1] == selected["damageModifier"][1])
        or len(contract.get("attributeCollectionSetters") or []) != 2
    ):
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
) -> dict[str, Any]:
    """Prove this source's populated root attribute child without the heal route."""
    if (prefix.get("schemaVersion") != 1
            or prefix["methods"][5] != heal["methods"][3]
            or len(prefix.get("codeWindows") or []) < 11
            or len(heal.get("wrapperSetters", {}).get("attributeModifier", [])) != 4
            or len(heal.get("attributeValueStores") or []) != 4):
        raise ValueError(f"{LABEL}.native:attribute-dependency-shape")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["GameAssembly.dll"], inputs["global-metadata.dat"],
    )
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail}
    image = open_native_image(gate.gameassembly, gate.metadata)
    for row in prefix["methods"][2:6]:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(prefix["codeWindows"][4:11] + [heal["codeWindows"][3]],
                        label=LABEL)
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


def validate_current_native_contract() -> dict[str, Any]:
    """Validate only the selected root and three relevant child contracts."""
    contract = _contract()
    native_inputs = contract["nativeInputs"]
    root, _ = read_reviewed_contract(
        ROOT_PATH, schema="endfield.buff-root-no-positive-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    prefix = json.loads(PREFIX_PATH.read_text(encoding="utf-8"))
    heal, _ = read_reviewed_contract(
        ATTRIBUTE_PATH, schema="endfield.buff-heal-processor-zero-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    parent, _ = read_reviewed_contract(
        MODIFIER_PATH, schema="endfield.buff-damage-modifier-child-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    condition, _ = read_reviewed_contract(
        SEQUENCE_PATH,
        schema="endfield.buff-damage-sequence-action-condition-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    child, _ = read_reviewed_contract(
        PROCESSOR_PATH,
        schema="endfield.buff-damage-modify-calc-result-processor-child-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    if any(row.get("nativeInputs") != native_inputs
           for row in (root, heal, parent, condition, child)):
        raise ValueError(f"{LABEL}.native:dependency-input-drift")
    root_validation = validate_root_native()
    if root_validation.get("status") != "validated":
        return {"status": root_validation.get("status", "failed"),
                "detail": root_validation.get("detail", "root native gate failed")}
    if root_validation.get("nativeInputs") != native_inputs:
        raise ValueError(f"{LABEL}.native:root-input-drift")
    attribute_validation = _validate_attribute_native(contract, prefix, heal)
    if attribute_validation.get("status") != "validated":
        return attribute_validation
    parent_validation = modifier.validate_current_native_contract()
    if parent_validation.get("status") != "validated":
        return {"status": parent_validation.get("status", "failed"),
                "detail": parent_validation.get("detail", "damage modifier gate failed")}
    condition_validation = sequence.validate_current_native_contract(
        modifier_native=parent_validation,
    )
    if condition_validation.get("status") != "validated":
        return {"status": condition_validation.get("status", "failed"),
                "detail": condition_validation.get("detail", "sequence gate failed")}
    child_validation = processor.validate_current_native_contract(
        modifier_native=parent_validation,
    )
    if (child_validation.get("status") != "validated"
            or child_validation.get("nativeInputs") != native_inputs
            or child_validation.get("unionTag") != child.get("unionTag")):
        return {"status": child_validation.get("status", "failed"),
                "detail": child_validation.get("detail", "tag-ten processor gate failed")}
    return {
        "status": "validated", "nativeInputs": native_inputs,
        "selectedSource": contract["selectedSource"],
        "root": root_validation, "attribute": attribute_validation,
        "modifier": parent_validation,
        "condition": condition_validation, "processorTen": child_validation,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_selected_source(data: bytes, *, source: str,
                           native_validation: dict[str, Any],
                           outer_row: dict[str, Any]) -> dict[str, Any]:
    contract = _contract()
    selected = contract["selectedSource"]
    if (native_validation.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native_validation.get("selectedSource") != selected
            or any(native_validation.get(name, {}).get("status") != "validated"
                   for name in ("root", "attribute", "modifier", "condition", "processorTen"))):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if (not isinstance(data, bytes) or source != selected["path"]
            or len(data) != selected["length"]
            or hashlib.sha256(data).hexdigest().upper() != selected["sha256"]):
        raise ValueError(f"{LABEL}.source:path-length-or-sha256")
    identity = outer_row.get("identity") or {}
    candidates = outer_row.get("candidates") or []
    prior = (candidates[0].get("namedSchemaReceipt") or {}) if len(candidates) == 1 else {}
    fields = prior.get("forwardNamedFields") or []
    attribute_field = fields[3] if len(fields) == 15 else {}
    field = fields[6] if len(fields) == 15 else {}
    if (identity.get("fileName") != source or identity.get("length") != len(data)
            or outer_row.get("logicalSha256") != selected["sha256"]
            or outer_row.get("coverageStatus") != "unique"
            or outer_row.get("candidateCount") != 1
            or prior.get("physicalEof") != len(data)
            or attribute_field.get("index") != 3
            or attribute_field.get("name") != "attributeModifier"
            or [attribute_field.get("start"), attribute_field.get("end")]
            != selected["attributeModifier"]
            or field.get("index") != 6 or field.get("name") != "damageModifier"
            or [field.get("start"), field.get("end")] != selected["damageModifier"]
            or field.get("count") != 1
            or field.get("recursiveNamedSchemaExact") is not False
            or {"field": "damageModifier", "category": "positive-modifier-recursive-proof",
                "start": selected["damageModifier"][0],
                "end": selected["damageModifier"][1]} not in (prior.get("blockers") or [])):
        raise ValueError(f"{LABEL}.outer:field-six-drift")
    attribute_start, attribute_end = selected["attributeModifier"]
    reader = _ResidualReader(data, source, attribute_end)
    reader.pos = attribute_start
    reader.modifier_collection_profile()
    if (reader.pos != attribute_end
            or len([row for row in reader.records
                    if row.get("kind") == "anonymous-modifier-element-profile"
                    and [row.get("start"), row.get("end")] == selected["attributeItem"]]) != 1
            or len([row for row in reader.records
                    if row.get("kind") == "anonymous-scalar-payload"
                    and [row.get("start"), row.get("end")] == selected["attributeParam"]]) != 1
            or data[attribute_start] != len(native_validation["attribute"]["collectionReadOrder"])
            or struct.unpack_from("<i", data, attribute_start + 1)[0] != 1
            or data[selected["attributeItem"][0]]
            != len(native_validation["attribute"]["itemReadOrder"])):
        raise ValueError(f"{LABEL}.attribute:cursor-or-count")
    param = blackboard.decode_adding_cooldown(
        data, *selected["attributeParam"],
        native_validation=native_validation["processorTen"]["blackboardChildNative"],
    )
    if (param.get("status") != "exact"
            or param.get("wholeValueExact") is not True
            or param.get("consumedEnd") != selected["attributeParam"][1]):
        raise ValueError(f"{LABEL}.attribute:param-incomplete")
    item_start, item_end = selected["attributeItem"]
    names = native_validation["attribute"]["itemReadOrder"]
    item_fields = []
    cursor = item_start + 1
    for name in names[:3]:
        item_fields.append({"name": name, "range": [cursor, cursor + 4],
                            "rawBitsHex": data[cursor:cursor + 4].hex().upper()})
        cursor += 4
    if cursor != selected["attributeParam"][0] or item_end != selected["attributeParam"][1]:
        raise ValueError(f"{LABEL}.attribute:item-fields")
    item_fields.append({"name": names[3], "range": selected["attributeParam"],
                        "child": param})
    attribute_receipt = {
        "start": attribute_start, "end": attribute_end,
        "memberNames": native_validation["attribute"]["collectionReadOrder"],
        "count": 1, "item": {"range": selected["attributeItem"], "fields": item_fields},
        "isConvertedAttribute": {"range": selected["attributeTerminal"],
                                 "rawByte": data[selected["attributeTerminal"][0]]},
        "wholeNamedSchemaExact": True,
    }
    start, end = selected["damageModifier"]
    parent = modifier.decode_damage_modifier_collection(
        data, start, end, source=source,
        native_validation=native_validation["modifier"],
    )
    elements = parent.get("elements") or []
    if (parent.get("status") != "named-direct-child-spans"
            or parent.get("count") != 1 or len(elements) != 1
            or [elements[0].get("start"), elements[0].get("end")] != selected["item"]):
        raise ValueError(f"{LABEL}.parent:item-count-or-span")
    members = elements[0].get("fields") or []
    if ([row.get("name") for row in members]
            != ["condition", "damageProcessors", "enableSide"]
            or [[members[0].get("start"), members[0].get("end")],
                [members[1].get("start"), members[1].get("end")],
                [members[2].get("start"), members[2].get("end")]]
            != [selected["condition"], selected["processors"], selected["enableSide"]]
            or members[0].get("actionUnionCount") != 0
            or members[0].get("actionTags") != []
            or members[1].get("count") != 1
            or len(members[1].get("processors") or []) != 1
            or [members[1]["processors"][0].get("start"),
                members[1]["processors"][0].get("end")]
            != selected["processorTen"]
            or members[1]["processors"][0].get("tag")
            != native_validation["processorTen"]["unionTag"]):
        raise ValueError(f"{LABEL}.parent:children-or-counts")
    condition = sequence.decode_zero_action_condition(
        data, source=source, start=selected["condition"][0],
        end=selected["condition"][1], logical_sha256=selected["sha256"],
        native_validation=native_validation["condition"],
    )
    if (condition.get("status") != "exact-empty-sequence"
            or condition.get("wholeStoredSpanExact") is not True):
        raise ValueError(f"{LABEL}.condition:incomplete")
    tag_ten = processor.decode_modify_calc_result_processor_span(
        data, source=source, logical_sha256=selected["sha256"],
        start=selected["processorTen"][0], end=selected["processorTen"][1],
        native_validation=native_validation["processorTen"],
    )
    if (tag_ten.get("status") != "named-direct-members-exact-span"
            or tag_ten.get("recursiveNamedSchemaExact") is not True
            or tag_ten.get("wholeStoredSpanExact") is not True
            or len(tag_ten.get("namedFields") or []) != 3):
        raise ValueError(f"{LABEL}.processor:incomplete")
    return {
        "schema": "endfield.buff-empty-condition-tag-ten-selected-receipt.v2",
        "status": "exact-selected-empty-condition-tag-ten",
        "source": source, "logicalSha256": selected["sha256"],
        "attributeModifier": attribute_receipt,
        "damageModifier": {"start": start, "end": end, "count": 1,
                           "parent": parent, "conditionChild": condition,
                           "processorChild": tag_ten,
                           "enableSide": members[2],
                           "wholeNamedSchemaExact": True},
        "wholeBuffDataExact": False, "publicationEligible": False,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--buff-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    native = validate_current_native_contract()
    if native.get("status") != "validated":
        raise SystemExit(f"{LABEL}.native:{native.get('status')}:{native.get('detail', '')}")
    report = json.loads(args.buff_report.read_text(encoding="utf-8"))
    if report.get("status") != "complete" or report.get("publicationEligible") is not True:
        raise SystemExit(f"{LABEL}.outer:report-not-complete")
    matches = [row for row in report.get("files", [])
               if row.get("identity", {}).get("fileName") == args.source]
    if len(matches) != 1:
        raise SystemExit(f"{LABEL}.outer:source-count={len(matches)}")
    result = decode_selected_source(
        args.input.read_bytes(), source=args.source,
        native_validation=native, outer_row=matches[0],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"], result["damageModifier"]["start"],
          result["damageModifier"]["end"])


if __name__ == "__main__":
    main()
