"""Source-bound selected sword damage child; root parsing belongs to its owner.

The existing recursive condition and tag-five processor are independently
reparsed on the original logical bytes. Two additional parent MethodSpec/type
joins close damageProcessors and enableSide. This module never reads or admits
the thirty-field BuffData root; buff_root_no_positive owns that composition.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run from the repository root: python -m scripts.game_data.memorypack.buff_damage_sword_selected")

from scripts.common import REPORTS_DIR, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier
from scripts.game_data.memorypack import buff_damage_scale_processor_child_receipt as processor
from scripts.game_data.memorypack import buff_damage_sequence_action_condition_receipt as sequence
from scripts.game_data.memorypack import buff_damage_sword_condition_receipt as condition
from scripts.game_data.memorypack import buff_root_no_positive_native as root_native


LABEL = "buffDamageSwordSelected"
SCHEMA = "endfield.buff-damage-sword-selected-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-sword-selected-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_sword_selected_native.json"
DEFAULT_NATIVE_AUDIT = REPORTS_DIR / "animestudio/il2cpp_context_current_latest.json"


def _public_native(value: Any) -> Any:
    """Private derived reader registries are rebuilt, never serialized as proof."""
    if isinstance(value, dict):
        return {key: _public_native(child) for key, child in value.items()
                if not isinstance(key, str) or not key.startswith("_")}
    if isinstance(value, (list, tuple)):
        return [_public_native(child) for child in value]
    return value


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=NATIVE_SCHEMA,
                                        status="exact-current-build", label=LABEL)
    selected = contract.get("selectedSource") or {}
    stored, _nested, serial = condition._declarations()
    expected_dependencies = [root_native.CONTRACT_PATH.name, modifier.CONTRACT_PATH.name,
                             condition.storage.CONTRACT_PATH.name,
                             sequence.CONTRACT_PATH.name, processor.CONTRACT_PATH.name]
    spans = ("damageModifier", "item", "processors", "processor", "enableSide")
    joins = contract.get("parentTypedChildren") or []
    if (contract.get("reviewedDependencies") != expected_dependencies
            or any(selected.get(key) != stored["selectedSource"].get(key) for key in ("path", "sha256"))
            or any(row.get("nativeInputs") != contract.get("nativeInputs") for row in
                   (stored, serial, root_native._contract(), modifier._contract(), processor._contract()))
            or type(selected.get("length")) is not int or selected["length"] <= 0
            or any(not isinstance(selected.get(key), list) or len(selected[key]) != 2
                   or any(type(value) is not int for value in selected[key])
                   or not 0 <= selected[key][0] < selected[key][1] <= selected["length"] for key in spans)
            or not (selected["damageModifier"][0] + 4 == selected["item"][0]
                    and selected["item"][0] + 1 == stored["selectedSource"]["conditionStart"]
                    and stored["selectedSource"]["conditionEnd"] == selected["processors"][0]
                    and selected["processors"][0] + 4 == selected["processor"][0]
                    and selected["processor"][1] == selected["processors"][1] == selected["enableSide"][0]
                    and selected["enableSide"][0] + 4 == selected["enableSide"][1]
                    == selected["item"][1] == selected["damageModifier"][1])
            or [row.get("fieldName") for row in joins] != modifier._contract()["selectedReadOrder"][1:]
            or any(row.get("sourceRole") != row["fieldName"] + " source context"
                   or type(row.get("methodSpecIndex")) is not int
                   or len(row.get("methodSpec") or []) != 3
                   or not isinstance(row.get("typeName"), str) for row in joins)):
        raise ValueError(f"{LABEL}.contract:dependency-or-shape-drift")
    return contract


def _parent_joins(contract: dict[str, Any]) -> list[dict[str, Any]]:
    provider = sequence._contract()["conditionProvider"]
    return [{"fieldName": modifier._contract()["selectedReadOrder"][0],
              "sourceRole": "condition source context", "methodOwner": "MemoryPack.MemoryPackReader",
              "methodName": "ReadValue", **provider}, *contract["parentTypedChildren"]]


def _typed_parent_children(image: Any, contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Resolve parent-selected calls and join actual setter/destination types."""
    parent = modifier._contract()
    joins = _parent_joins(contract)
    owner_name = parent["childDestinationField"].partition("::")[0]
    owner = modifier._selected_type(image, owner_name)
    destination_fields = {image.metadata.string(row.name_index): row for row in image.metadata.fields_for(owner)}
    sources = {row[2]: row for row in parent["childSourceInstructions"]}
    setters = {row[1].removeprefix("set___").removesuffix("__"): row for row in parent["childSetters"]}
    result = []
    for join in joins:
        name = join["fieldName"]
        site = sources[join["sourceRole"]]
        prefix = f"{LABEL}.native field={name} source={image.gameassembly} instructionRva={site[0]} "
        image.check_instruction_windows([site], label=LABEL)
        raw = image.pe.bytes_at_va(image.pe.image_base + site[0], 7)
        if raw[:3] != b"\x48\x8b\x15":
            raise ValueError(prefix + f"check=context-instruction expected=488B15 actual={raw.hex().upper()}")
        cell = image.pe.image_base + site[0] + 7 + struct.unpack_from("<i", raw, 3)[0]
        usage = image.pe.bytes_at_va(cell, 8)
        index = method_spec_usage_index(usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell)
        spec = list(struct.unpack("<iii", image.pe.bytes_at_va(int(image.registration["methodSpecs"], 16) + index * 12, 12)))
        if index != join["methodSpecIndex"] or spec != join["methodSpec"]:
            raise ValueError(prefix + f"check=method-spec expected={join['methodSpecIndex']}:{join['methodSpec']} actual={index}:{spec}")
        method = image.metadata.methods[spec[0]]
        method_owner = image.type_name(method.declaring_type)
        method_name = image.metadata.string(method.name_index)
        arguments = image.instantiations.resolve(spec[2]).arguments
        if (method_owner != join["methodOwner"] or method_name != join["methodName"]
                or spec[1] != -1 or len(arguments) != 1
                or arguments[0].raw_type_record_hex != join["argumentRawHex"]):
            raise ValueError(prefix + f"check=typed-method expected={join['methodOwner']}.{join['methodName']}<{join['typeName']}> actual={method_owner}.{method_name} argumentCount={len(arguments)}")
        argument_type = runtime_type_name(image.pe, image.metadata, arguments[0].type_pointer_va)
        parameters = image.metadata.parameters_for(image.metadata.methods[setters[name][0]])
        if len(parameters) != 1 or name not in destination_fields:
            raise ValueError(prefix + "check=destination expected=one setter parameter and named field actual=missing")
        types = int(image.registration["types"], 16)
        setter_type = runtime_type_name(image.pe, image.metadata, image.pe.u64_at_va(types + parameters[0].type_index * 8))
        field_type = runtime_type_name(image.pe, image.metadata, image.pe.u64_at_va(types + destination_fields[name].type_index * 8))
        if argument_type != join["typeName"] or setter_type != argument_type or field_type != argument_type:
            raise ValueError(prefix + f"check=type-join expected={join['typeName']} actualArgument={argument_type} actualSetter={setter_type} actualField={field_type}")
        result.append({"fieldName": name, "instructionRva": site[0], "methodSpecIndex": index,
                       "typeName": argument_type, "setterType": setter_type, "destinationFieldType": field_type})
    return result


def validate_current_native_contract(audit_report_path: Path = DEFAULT_NATIVE_AUDIT, *,
                                    gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"],
                                         gameassembly=gameassembly, metadata=metadata)
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "failedChild": "selectedNativeInputs"}
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "missing" if not unity.is_file() else "mismatched", "detail": "selected UnityPlayer.dll missing or hash differs", "failedChild": "selectedNativeInputs"}
    validations = {}
    for name, validate in (("root", lambda: root_native.validate_current_native_contract(
                               gameassembly=gate.gameassembly, metadata=gate.metadata)),
                           ("modifier", lambda: modifier.validate_current_native_contract(
                               gameassembly=gate.gameassembly, metadata=gate.metadata)),
                           ("condition", lambda: condition.validate_current_native_contract(
                               audit_report_path, gameassembly=gate.gameassembly, metadata=gate.metadata))):
        value = validate()
        if value.get("status") != "validated":
            return {"status": value.get("status", "failed"), "detail": str(value.get("detail", "native child failed"))[:500], "failedChild": name}
        validations[name] = value
    validations["processor"] = processor.validate_current_native_contract(modifier_native=validations["modifier"],
                                gameassembly=gate.gameassembly, metadata=gate.metadata)
    if validations["processor"].get("status") != "validated":
        return {"status": validations["processor"].get("status", "failed"), "detail": validations["processor"].get("detail"), "failedChild": "processor"}
    if any(validations[name].get("nativeInputs") != expected for name in ("root", "condition", "processor")):
        raise ValueError(f"{LABEL}.native:child-build-drift")
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_method_row(modifier._contract()["childMethod"], label=LABEL)
    image.check_windows([modifier._contract()["childWindow"]], label=LABEL)
    typed = _typed_parent_children(image, contract)
    return {"status": "validated", "nativeInputs": expected, "selectedSource": contract["selectedSource"],
            "selectedNativePaths": {"GameAssembly.dll": str(gate.gameassembly), "global-metadata.dat": str(gate.metadata)},
            "nativeAuditPath": str(Path(audit_report_path).resolve()),
            "parentTypedChildren": typed, **_public_native(validations)}


def _current_condition_native(native: dict[str, Any]) -> dict[str, Any]:
    paths = native.get("selectedNativePaths") or {}
    if set(paths) != {"GameAssembly.dll", "global-metadata.dat"} or not native.get("nativeAuditPath"):
        raise ValueError(f"{LABEL}.native:missing-selected-paths-or-audit")
    current = condition.validate_current_native_contract(Path(native["nativeAuditPath"]),
            gameassembly=Path(paths["GameAssembly.dll"]), metadata=Path(paths["global-metadata.dat"]))
    if current.get("status") != "validated" or _public_native(current) != native["condition"]:
        raise ValueError(f"{LABEL}.native:condition-replay-certificate-drift actual={current.get('status')}")
    return current


def _check_outer(data: bytes, source: str, selected: dict[str, Any], outer: dict[str, Any]) -> None:
    candidates = outer.get("candidates") or []
    prior = (candidates[0].get("namedSchemaReceipt") or {}) if len(candidates) == 1 else {}
    fields = prior.get("forwardNamedFields") or []
    field = fields[6] if len(fields) == 15 else {}
    identity = outer.get("identity") or {}
    if (identity.get("fileName") != source or identity.get("length") != len(data)
            or identity.get("status") != "verified" or identity.get("boundaryStatus") != "boundary_verified"
            or outer.get("logicalSha256") != selected["sha256"]
            or outer.get("coverageStatus") != "unique" or outer.get("candidateCount") != 1
            or prior.get("physicalEof") != len(data) or field.get("index") != 6
            or field.get("name") != root_native._contract()["fields"][6]["name"]
            or [field.get("start"), field.get("end")] != selected["damageModifier"] or field.get("count") != 1):
        raise ValueError(f"{LABEL}.outer:field-six-or-source-drift source={source}")


def decode_selected_source(data: bytes, *, source: str, native_validation: dict[str, Any],
                           outer_row: dict[str, Any]) -> dict[str, Any]:
    contract = _contract()
    selected = contract["selectedSource"]
    native = native_validation
    expected_names = modifier._contract()["selectedReadOrder"]
    typed = native.get("parentTypedChildren") or []
    expected_joins = _parent_joins(contract)
    if (native.get("status") != "validated" or native.get("nativeInputs") != contract["nativeInputs"]
            or native.get("selectedSource") != selected
            or any(native.get(name, {}).get("status") != "validated" for name in ("root", "modifier", "condition", "processor"))
            or any(native.get(name, {}).get("nativeInputs") != contract["nativeInputs"] for name in ("root", "condition", "processor"))
            or [row.get("fieldName") for row in typed] != expected_names
            or any(row.get("typeName") != expected["typeName"]
                   or row.get("methodSpecIndex") != expected["methodSpecIndex"]
                   or row.get("typeName") != row.get("setterType")
                   or row.get("typeName") != row.get("destinationFieldType")
                   for row, expected in zip(typed, expected_joins))):
        raise ValueError(f"{LABEL}.native:incomplete-parent-or-child-proof")
    digest = hashlib.sha256(data).hexdigest().upper()
    if source != selected["path"] or digest != selected["sha256"] or len(data) != selected["length"]:
        raise ValueError(f"{LABEL}.source:path-length-or-sha256 expected={selected} actual={source}:{len(data)}:{digest}")
    _check_outer(data, source, selected, outer_row)
    start, end = selected["damageModifier"]
    parent = modifier.decode_damage_modifier_collection(data, start, end, source=source,
                native_validation=native["modifier"], processor_native_validation=native["processor"])
    elements = parent.get("elements") or []
    members = elements[0].get("fields") or [] if len(elements) == 1 else []
    selected_condition = condition.storage._contract()["selectedSource"]
    condition_span = [selected_condition["conditionStart"], selected_condition["conditionEnd"]]
    if (parent.get("status") != "named-direct-child-spans" or parent.get("count") != 1
            or parent.get("startOffset") != start or parent.get("consumedEnd") != end
            or len(elements) != 1 or [elements[0].get("start"), elements[0].get("end")] != selected["item"]
            or [row.get("name") for row in members] != expected_names
            or [[row.get("start"), row.get("end")] for row in members]
               != [condition_span, selected["processors"], selected["enableSide"]]):
        raise ValueError(f"{LABEL}.parent:count-member-or-tiling-drift")
    stored_condition = condition.decode_selected_condition(data, source=source,
                            native_validation=_current_condition_native(native))
    processors = members[1].get("processors") or []
    if (stored_condition.get("wholeConditionStoredSchemaExact") is not True
            or stored_condition.get("recursiveNamedSchemaExact") is not True
            or [stored_condition.get("start"), stored_condition.get("end")] != condition_span
            or stored_condition.get("source") != source or stored_condition.get("logicalSha256") != digest
            or members[0].get("actionUnionCount") != stored_condition.get("topLevelActionCount", 0) + stored_condition.get("nestedActionCount", 0)
            or members[1].get("count") != 1 or len(processors) != 1
            or [processors[0].get("start"), processors[0].get("end")] != selected["processor"]
            or processors[0].get("tag") != native["processor"]["unionTag"]):
        raise ValueError(f"{LABEL}.condition-or-processor:incomplete")
    scale = processors[0].get("namedChild") or {}
    if (scale.get("recursiveNamedSchemaExact") is not True or scale.get("wholeStoredSpanExact") is not True
            or scale.get("source") != source or scale.get("logicalSha256") != digest
            or [scale.get("start"), scale.get("end")] != selected["processor"]
            or [row.get("name") for row in scale.get("namedFields") or []]
               != [row["name"] for row in native["processor"]["fieldPlan"]]):
        raise ValueError(f"{LABEL}.processor:recursive-child-incomplete")
    enable = {**members[2], "declaredType": typed[-1]["typeName"],
              "storedInt32": struct.unpack_from("<i", data, selected["enableSide"][0])[0]}
    damage = {"status": "exact-selected-sword-damage-list", "start": start, "end": end,
              "startOffset": start, "consumedEnd": end, "count": 1, "parent": parent,
              "conditionChild": stored_condition, "processorChild": scale, "enableSide": enable,
              "wholeListExact": True, "wholeNamedSchemaExact": True, "recursiveNamedSchemaExact": True}
    return {"schema": SCHEMA, "status": "exact-selected-sword-damage-child", "source": source,
            "logicalSha256": digest, "damageModifier": damage, "selectedOnly": True,
            "publicationEligible": False, "wholeBuffDataExact": False, "runtimeBehaviorObserved": False,
            "evidenceBoundary": contract["evidenceBoundary"]}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("gameassembly", "metadata", "audit-report", "source-file", "outer-row", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    protected = [args.source_file, args.outer_row, args.gameassembly, args.metadata, args.audit_report,
                 args.gameassembly.parent / "UnityPlayer.dll"]
    try:
        output = condition._guard_cli_output(args.output, protected)
    except ValueError as exc:
        parser.error(str(exc))
    native = validate_current_native_contract(args.audit_report, gameassembly=args.gameassembly, metadata=args.metadata)
    if native.get("status") != "validated":
        print(json.dumps(native)); return 1
    receipt = decode_selected_source(args.source_file.read_bytes(), source=native["selectedSource"]["path"],
                                    native_validation=native, outer_row=json.loads(args.outer_row.read_bytes()))
    output = condition._guard_cli_output(output, protected)
    atomic_write_text(output, json.dumps({"schema": SCHEMA, "status": "validated-selected-sword-damage-child",
                                        "publicationEligible": False, "nativeValidation": native,
                                        "receipt": receipt}, indent=2) + "\n")
    print(json.dumps({"status": "validated-selected-sword-damage-child", "wholeBuffDataExact": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
