"""Selected native receipt for one positive HealModifier tag-zero processor.

This joins the direct wrapper source reads to generated setters and the
selected original bytes. A separate root composition decides whether those
children close the enclosing BuffData source.
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
from scripts.game_data.il2cpp.context import method_spec_usage_index, unresolved_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.memorypack import buff_adding_cooldown as blackboard
from scripts.game_data.memorypack import buff_heal_check_tag_selected as condition
from scripts.game_data.memorypack.buff_actions import Reader


LABEL = "buffHealProcessorZero"
SCHEMA = "endfield.buff-heal-processor-zero-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_heal_processor_zero_native.json"
BLACKBOARD_PATH = CONTRACTS_DIR / "buff_adding_cooldown_ownership_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL,
    )
    selected = contract.get("selectedSource") or {}
    path = selected.get("path")
    spans = ("healModifier", "condition", "enableSide", "healProcessors",
             "processorZero", "modifier", "attributeType", "formulaItem",
             "modifyAttributeType", "param", "modifyTargetSide")
    methods = contract.get("methods") or []
    windows = contract.get("codeWindows") or []
    setters = contract.get("wrapperSetters") or {}
    calls = contract.get("sourceCalls") or {}
    contexts = contract.get("genericContexts") or []
    if (
        contract.get("reviewedDependencies")
        != [condition.CONTRACT_PATH.name, BLACKBOARD_PATH.name]
        or not isinstance(path, str)
        or PurePosixPath(path).parts[:3] != ("Data", "Json", "BuffData")
        or len(PurePosixPath(path).parts) != 4 or not path.endswith(".json")
        or not isinstance(selected.get("sha256"), str)
        or len(selected["sha256"]) != 64
        or any(ch not in "0123456789ABCDEF" for ch in selected["sha256"])
        or type(selected.get("length")) is not int or selected["length"] <= 0
        or any(not isinstance(selected.get(key), list)
               or len(selected[key]) != 2
               or any(type(offset) is not int for offset in selected[key])
               or not 0 <= selected[key][0] < selected[key][1] <= selected["length"]
               for key in spans)
        or not (selected["healModifier"][0] < selected["condition"][0]
                < selected["condition"][1] == selected["enableSide"][0]
                < selected["enableSide"][1] == selected["healProcessors"][0]
                < selected["processorZero"][0] < selected["modifier"][0]
                < selected["attributeType"][0]
                < selected["attributeType"][1] == selected["formulaItem"][0]
                < selected["formulaItem"][1] == selected["modifyAttributeType"][0]
                < selected["modifyAttributeType"][1] == selected["param"][0]
                < selected["param"][1] == selected["modifier"][1]
                == selected["modifyTargetSide"][0]
                < selected["modifyTargetSide"][1] == selected["processorZero"][1]
                == selected["healProcessors"][1] == selected["healModifier"][1])
        or len(methods) != 4 or any(len(row) != 4 for row in methods)
        or len(windows) != 4
        or set(setters) != {"healModifier", "processorZero", "attributeModifier"}
        or [len(setters[key]) for key in setters] != [3, 2, 4]
        or set(calls) != set(setters)
        or [len(calls[key]) for key in calls] != [6, 4, 4]
        or len(contexts) != 8
        or len({row.get("role") for row in contexts}) != len(contexts)
        or not isinstance(contract.get("attributeValueFieldOffsets"), dict)
        or len(contract.get("attributeValueStores") or []) != 4
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    previous = condition._contract()
    if (contract["nativeInputs"] != previous["nativeInputs"]
            or {key: selected[key] for key in ("path", "sha256", "length",
                                                 "healModifier", "condition")}
            != {key: previous["selectedSource"][key] for key in
                ("path", "sha256", "length", "healModifier", "condition")}):
        raise ValueError(f"{LABEL}.contract:selection-drift")
    return contract


def _selected_type(image: Any, name: str) -> Any:
    rows = [row for row in image.metadata.types
            if image.metadata.type_full_name(row) == name]
    if len(rows) != 1:
        raise ValueError(f"{LABEL}.native:type={name}; matches={len(rows)}")
    return rows[0]


def _verify_call(image: Any, row: dict[str, Any]) -> None:
    rva = row["instructionRva"]
    raw = bytes.fromhex(row["rawHex"])
    if (len(raw) != 5 or raw[0] != 0xE8
            or image.pe.bytes_at_va(image.pe.image_base + rva, 5) != raw
            or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != row["targetRva"]):
        raise ValueError(f"{LABEL}.native:call={row['role']}")


def validate_current_native_contract(audit_report: dict[str, Any]) -> dict[str, Any]:
    """Gate only this source's four methods and their direct read paths."""
    contract = _contract()
    prior = condition.validate_current_native_contract(audit_report)
    if prior.get("status") != "validated":
        return {"status": prior.get("status", "failed"),
                "detail": prior.get("detail", "condition native gate failed")}
    child = blackboard.validate_current_native_contract()
    if child.get("status") != "validated":
        return {"status": child.get("status", "failed"),
                "detail": child.get("detail", "BlackboardDouble native gate failed")}
    child_contract, _ = read_reviewed_contract(
        BLACKBOARD_PATH, schema=blackboard.SCHEMA,
        status="exact-current-build", label=LABEL,
    )
    if (child_contract.get("nativeInputs") != contract["nativeInputs"]
            or child.get("selectedReadOrder") != child_contract.get("selectedReadOrder")):
        raise ValueError(f"{LABEL}.native:blackboard-dependency-drift")
    gate = check_installed_native_inputs(
        contract["nativeInputs"]["GameAssembly.dll"],
        contract["nativeInputs"]["global-metadata.dat"],
    )
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail}
    image = open_native_image(gate.gameassembly, gate.metadata)
    for row in contract["methods"]:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(contract["codeWindows"], label=LABEL)

    dispatcher = contract["dispatcher"]
    _verify_call(image, dispatcher["tagRead"])
    for rva, raw_hex in (dispatcher["zeroTest"], dispatcher["nonzeroBranch"]):
        raw = bytes.fromhex(raw_hex)
        if image.pe.bytes_at_va(image.pe.image_base + rva, len(raw)) != raw:
            raise ValueError(f"{LABEL}.native:tag-zero-branch")
    if (bytes.fromhex(dispatcher["zeroTest"][1]) != b"\x66\x85\xf6"
            or bytes.fromhex(dispatcher["nonzeroBranch"][1])[:1] != b"\x75"):
        raise ValueError(f"{LABEL}.native:tag-zero-test-shape")
    selected_type = dispatcher["tagZeroType"]
    cell, usage = image.nested_usage_cell(selected_type, label=LABEL)
    index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1,
        source=str(image.gameassembly), offset=cell,
    )
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    definition = struct.unpack_from("<Q", image.pe.bytes_at_va(pointer, 16))[0]
    if (index != selected_type["registeredTypeIndex"]
            or definition != selected_type["typeDefinition"]
            or image.type_name(definition) != selected_type["typeName"]
            or selected_type["typeName"] != contract["methods"][2][1]):
        raise ValueError(f"{LABEL}.native:tag-zero-type")

    groups = contract["wrapperSetters"]
    owner_names = {
        "healModifier": contract["methods"][1][1],
        "processorZero": contract["methods"][2][1],
        "attributeModifier": contract["methods"][3][1],
    }
    for group, owner_name in owner_names.items():
        owner = _selected_type(image, owner_name)
        expected = groups[group]
        if image.setter_methods(owner, parameter="typeName", label=LABEL) != [
                row[:3] for row in expected]:
            raise ValueError(f"{LABEL}.native:setter-order={group}")
        for row in expected:
            image.validate_method_row([row[0], owner_name, row[1], row[3]], label=LABEL)

    for group, rows in contract["sourceCalls"].items():
        if [row["instructionRva"] for row in rows] != sorted(
                row["instructionRva"] for row in rows):
            raise ValueError(f"{LABEL}.contract:source-call-order={group}")
        for row in rows:
            _verify_call(image, row)
        if group != "attributeModifier":
            if [rows[i]["targetRva"] for i in range(1, len(rows), 2)] != [
                    row[3] for row in groups[group]]:
                raise ValueError(f"{LABEL}.native:setter-call-targets={group}")

    for context in contract["genericContexts"]:
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"],
            source=str(image.gameassembly), offset=cell,
        )
        spec = list(struct.unpack("<iii", image.pe.bytes_at_va(
            int(image.registration["methodSpecs"], 16) + index * 12, 12,
        )))
        args = image.instantiations.resolve(spec[2]).arguments
        if (index != context["methodSpecIndex"] or spec != context["methodSpec"]
                or len(args) != 1
                or args[0].raw_type_record_hex != context["argumentRawHex"]
                or image.type_name(struct.unpack_from(
                    "<I", bytes.fromhex(context["argumentRawHex"]))[0])
                != context["typeName"]):
            raise ValueError(f"{LABEL}.native:generic-context={context['role']}")

    value_owner = _selected_type(image, groups["processorZero"][0][2])
    actual_offsets = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, value_owner.index,
    )
    if actual_offsets != contract["attributeValueFieldOffsets"]:
        raise ValueError(f"{LABEL}.native:attribute-field-offsets")
    for rva, raw_hex, role in contract["attributeValueStores"]:
        raw = bytes.fromhex(raw_hex)
        expected = (b"\x48\x89\x41" if role == "param" else b"\x89\x41")
        if (image.pe.bytes_at_va(image.pe.image_base + rva, len(raw)) != raw
                or raw[:-1] != expected or raw[-1] != actual_offsets[role]):
            raise ValueError(f"{LABEL}.native:attribute-store={role}")
    return {
        "status": "validated", "nativeInputs": contract["nativeInputs"],
        "selectedSource": contract["selectedSource"],
        "conditionNative": prior, "blackboardNative": child,
        "readOrders": {key: [row[1].removeprefix("set___").removesuffix("__")
                             for row in rows] for key, rows in groups.items()},
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
            or native_validation.get("blackboardNative", {}).get("status") != "validated"):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if (not isinstance(data, bytes) or source != selected["path"]
            or len(data) != selected["length"]
            or hashlib.sha256(data).hexdigest().upper() != selected["sha256"]):
        raise ValueError(f"{LABEL}.source:path-length-or-sha256")
    prior = condition.decode_selected_source(
        data, source=source, native_validation=native_validation["conditionNative"],
        outer_row=outer_row,
    )
    field_end = selected["healModifier"][1]
    reader = Reader(data, source, field_end)
    reader.pos = selected["healModifier"][0]
    if reader.heal_modifier_collection_profile() != 1 or reader.pos != field_end:
        raise ValueError(f"{LABEL}.field:count-or-end")
    for key, kind, variant in (
        ("condition", "sequence", None),
        ("processorZero", "anonymous-heal-processor-profile", 0),
        ("modifier", "anonymous-modifier-element-profile", None),
    ):
        start, end = selected[key]
        matches = [row for row in reader.records if row.get("kind") == kind
                   and [row.get("start"), row.get("end")] == [start, end]]
        if len(matches) != 1 or (variant is not None
                                 and matches[0].get("variant") != variant):
            raise ValueError(f"{LABEL}.cursor:{key}")
    # Field boundaries are proven by the selected forward cursor. The native
    # methods independently fix the direct member order at those boundaries.
    if (data[selected["healModifier"][0]:selected["healModifier"][0] + 4]
            != struct.pack("<i", 1)
            or data[selected["healModifier"][0] + 4] != 3
            or data[selected["healProcessors"][0]:selected["healProcessors"][0] + 4]
            != struct.pack("<i", 1)
            or data[selected["processorZero"][0]] != 0
            or data[selected["processorZero"][0] + 1] != 2
            or data[selected["modifier"][0]] != 4):
        raise ValueError(f"{LABEL}.cursor:headers")
    child = blackboard.decode_adding_cooldown(
        data, *selected["param"],
        native_validation=native_validation["blackboardNative"],
    )
    if child.get("status") != "exact" or child.get("consumedEnd") != selected["param"][1]:
        raise ValueError(f"{LABEL}.param:child-drift")
    def bits(key: str) -> str:
        start, end = selected[key]
        if end - start != 4:
            raise ValueError(f"{LABEL}.field-width={key}")
        return data[start:end].hex().upper()
    member_names = native_validation["readOrders"]
    if (member_names["healModifier"]
            != ["condition", "enableSide", "healProcessors"]
            or member_names["processorZero"] != ["modifier", "modifyTargetSide"]
            or member_names["attributeModifier"]
            != ["attributeType", "formulaItem", "modifyAttributeType", "param"]):
        raise ValueError(f"{LABEL}.native:member-order-drift")
    return {
        "schema": "endfield.buff-heal-processor-zero-selected-receipt.v1",
        "status": "selected-heal-processor-named-exact",
        "source": source, "logicalSha256": selected["sha256"],
        "condition": prior,
        "healModifier": {"start": selected["healModifier"][0],
                         "end": selected["healModifier"][1],
                         "memberNames": member_names["healModifier"],
                         "conditionRange": selected["condition"],
                         "enableSide": {"range": selected["enableSide"],
                                        "rawBitsHex": bits("enableSide")},
                         "healProcessorsRange": selected["healProcessors"],
                         "wholeNamedSchemaExact": (
                             prior["condition"]["wholeNamedSchemaExact"] is True
                             and prior["action"]["wholeNamedSchemaExact"] is True
                         )},
        "processor": {"tag": 0, "start": selected["processorZero"][0],
                      "end": selected["processorZero"][1],
                      "memberNames": member_names["processorZero"],
                      "modifier": {"range": selected["modifier"],
                                   "memberNames": member_names["attributeModifier"],
                                   "fields": [
                                       {"name": key, "range": selected[key],
                                        "rawBitsHex": bits(key)}
                                       for key in member_names["attributeModifier"][:3]
                                   ] + [{"name": "param", "range": selected["param"],
                                         "child": child}]},
                      "modifyTargetSide": {"range": selected["modifyTargetSide"],
                                           "rawBitsHex": bits("modifyTargetSide")},
                      "wholeStoredSchemaExact": True,
                      "liveBehaviorObserved": False},
        "wholeBuffDataExact": False, "publicationEligible": False,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--audit-report", type=Path, required=True)
    parser.add_argument("--buff-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit_report.read_text(encoding="utf-8"))
    native = validate_current_native_contract(audit)
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
    print(result["status"], result["processor"]["start"], result["processor"]["end"])


if __name__ == "__main__":
    main()
