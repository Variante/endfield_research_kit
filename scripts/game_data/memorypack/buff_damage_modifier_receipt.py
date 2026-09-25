"""Selected-build child ownership receipt for BuffData.damageModifier.

This partitions a positive modifier list into named child fields. Nested
conditions and processors retain the exact structural reader's evidence tier;
the receipt never claims a recursively named BuffData schema.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.memorypack.buff_residual_actions import _ResidualReader


CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_modifier_child_native.json"
ROOT_CONTRACT_PATH = CONTRACTS_DIR / "buff_root_prefix_native.json"
SCHEMA = "endfield.buff-damage-modifier-child-native-contract.v1"
LABEL = "buffDamageModifierChild"


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL
    )
    return value


def _selected_type(image: Any, name: str) -> Any:
    matches = [row for row in image.metadata.types
               if image.metadata.type_full_name(row) == name]
    if len(matches) != 1:
        raise ValueError(f"{LABEL}.native:type={name}; matches={len(matches)}")
    return matches[0]


def _call_target(image: Any, rva: int) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8:
        raise ValueError(f"{LABEL}.native:expected-direct-call={rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def validate_current_native_contract() -> dict[str, Any]:
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail,
                "evidenceBoundary": "No child field labels on missing or mismatched native inputs."}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "detail": f"{unity} is absent"}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "mismatched", "detail": "UnityPlayer.dll hash differs"}

    image = open_native_image(gate.gameassembly, gate.metadata)
    if contract["reviewedDependencies"] != [ROOT_CONTRACT_PATH.name]:
        raise ValueError(f"{LABEL}.native:dependency-list")
    root = json.loads(ROOT_CONTRACT_PATH.read_text(encoding="utf-8"))
    if root.get("schemaVersion") != 1 or contract["rootMethod"] != root["methods"][1]:
        raise ValueError(f"{LABEL}.native:root-contract")
    image.validate_method_row(contract["rootMethod"], label=LABEL)
    image.check_windows(root["codeWindows"], label=LABEL)

    context = contract["rootContext"]
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=str(image.gameassembly), offset=cell
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:root-method-spec-index")
    spec = struct.unpack("<iii", image.pe.bytes_at_va(
        int(image.registration["methodSpecs"], 16) + index * 12, 12
    ))
    if list(spec) != context["methodSpec"]:
        raise ValueError(f"{LABEL}.native:root-method-spec")
    args = image.instantiations.resolve(spec[2]).arguments
    if len(args) != 1 or args[0].raw_type_record_hex != context["argumentRawHex"]:
        raise ValueError(f"{LABEL}.native:root-generic-argument")
    pointer = struct.unpack_from("<Q", bytes.fromhex(args[0].raw_type_record_hex))[0]
    carrier = image.pe.bytes_at_va(pointer, 32)
    if carrier.hex().upper() != context["genericCarrierRawHex"]:
        raise ValueError(f"{LABEL}.native:root-generic-carrier")
    base_pointer, inst_pointer = struct.unpack_from("<QQ", carrier)
    base = image.pe.bytes_at_va(base_pointer, 16)
    if base.hex().upper() != context["genericBaseRawHex"]:
        raise ValueError(f"{LABEL}.native:root-generic-base")
    if image.type_name(struct.unpack_from("<I", base)[0]) != context["genericType"]:
        raise ValueError(f"{LABEL}.native:root-generic-type")
    element_inst = image.instantiations.resolve_pointer(inst_pointer)
    if (element_inst.index != context["elementInstantiationIndex"]
            or len(element_inst.arguments) != 1
            or element_inst.arguments[0].raw_type_record_hex != context["elementRawHex"]):
        raise ValueError(f"{LABEL}.native:root-element-instantiation")
    element_definition = struct.unpack_from("<I", bytes.fromhex(context["elementRawHex"]))[0]
    if image.type_name(element_definition) != context["elementType"]:
        raise ValueError(f"{LABEL}.native:root-element-type")

    image.check_instruction_windows(contract["rootSourceInstructions"], label=LABEL)
    root_owner, _, root_field = contract["rootDestinationField"].partition("::")
    root_offset = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, _selected_type(image, root_owner).index
    )[root_field]
    if root_offset != 0x40 or bytes.fromhex(contract["rootSourceInstructions"][1][1]) != bytes((0x48, 0x89, 0x41, root_offset)):
        raise ValueError(f"{LABEL}.native:root-field-store")
    if not (context["instructionRva"] < contract["rootSourceInstructions"][0][0]
            < contract["rootSourceInstructions"][1][0]):
        raise ValueError(f"{LABEL}.native:root-source-order")

    image.validate_method_row(contract["childMethod"], label=LABEL)
    image.check_windows([contract["childWindow"]], label=LABEL)
    owner = _selected_type(image, contract["childWrapper"])
    setters = image.setter_methods(owner, parameter="typeName", label=LABEL)
    if setters != [row[:3] for row in contract["childSetters"]]:
        raise ValueError(f"{LABEL}.native:child-setters")
    for row in contract["childSetters"]:
        image.validate_method_row([row[0], contract["childWrapper"], row[1], row[3]], label=LABEL)
    image.check_instruction_windows(contract["childSourceInstructions"], label=LABEL)
    instructions = contract["childSourceInstructions"]
    if not all(instructions[i][0] < instructions[i + 1][0] for i in range(len(instructions) - 1)):
        raise ValueError(f"{LABEL}.native:child-source-order")
    for call_index, setter_index in ((3, 0), (6, 1)):
        if _call_target(image, instructions[call_index][0]) != contract["childSetters"][setter_index][3]:
            raise ValueError(f"{LABEL}.native:child-setter-call")
    child_owner, _, child_field = contract["childDestinationField"].partition("::")
    child_offset = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, _selected_type(image, child_owner).index
    )[child_field]
    if child_offset != 0x10 or bytes.fromhex(instructions[-1][1]) != bytes((0x89, 0x41, child_offset)):
        raise ValueError(f"{LABEL}.native:child-field-store")
    return {"status": "validated", "selectedReadOrder": contract["selectedReadOrder"],
            "rootField": contract["rootDestinationField"],
            "childWrapper": contract["childWrapper"],
            "evidenceBoundary": contract["evidenceBoundary"]}


def decode_damage_modifier_collection(
    data: bytes, start: int, end: int, *, source: str,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Partition one already bounded positive list; preserve nested refusals."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError(f"{LABEL}.boundary:invalid")
    reader = _ResidualReader(data, source, end)
    reader.pos = start
    count = reader.count(1, nullable=True)
    if count <= 0:
        raise ValueError(f"{LABEL}.count:expected-positive actual={count}")
    elements = []
    for index in range(count):
        element_start = reader.pos
        if reader.peek() == 0xFF:
            reader.take(1, "null-damage-modifier-element")
            elements.append({"index": index, "start": element_start, "end": reader.pos,
                             "status": "exact-null", "fields": []})
            continue
        reader.header(3)
        condition_start = reader.pos
        record_start = len(reader.records)
        reader.sequence()
        condition_end = reader.pos
        condition_actions = [row for row in reader.records[record_start:]
                             if row.get("kind") == "union"]
        processor_start = reader.pos
        processor_count = reader.count(1, reserve=4, nullable=True)
        processors = []
        for processor_index in range(max(0, processor_count)):
            item_start = reader.pos
            reader.damage_processor_profile()
            record = reader.records[-1]
            processors.append({"index": processor_index, "start": item_start,
                               "end": reader.pos, "tag": record.get("variant")})
        processor_end = reader.pos
        side_start = reader.pos
        raw_side = reader.take(4, "damage-modifier-enable-side")
        elements.append({
            "index": index, "start": element_start, "end": reader.pos,
            "status": "named-direct-child-spans",
            "headerRange": [element_start, element_start + 1],
            "fields": [
                {"name": "condition", "start": condition_start, "end": condition_end,
                 "actionUnionCount": len(condition_actions),
                 "actionTags": [row["tag"] for row in condition_actions],
                 "recursiveNamedSchemaExact": False},
                {"name": "damageProcessors", "start": processor_start,
                 "end": processor_end, "count": processor_count,
                 "processors": processors, "recursiveNamedSchemaExact": False},
                {"name": "enableSide", "start": side_start, "end": reader.pos,
                 "rawBitsHex": raw_side.hex().upper(), "recursiveNamedSchemaExact": True},
            ],
        })
    if reader.pos != end:
        raise ValueError(f"{LABEL}.cursor:expected={end} actual={reader.pos}")
    return {"status": "named-direct-child-spans", "startOffset": start,
            "consumedEnd": end, "count": count, "elements": elements,
            "conditionActionUnionCount": sum(field["fields"][0]["actionUnionCount"]
                                             for field in elements if field["fields"]),
            "wholeValueExact": False,
            "evidenceBoundary": "Direct selected child field ownership and exact stored cursors; nested actions and processor members remain unresolved."}


def audit_first_blockers(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str
) -> dict[str, Any]:
    report_raw = report_path.read_bytes()
    report = json.loads(report_raw)
    expected_input = expected_input_set_sha256.upper()
    if (not re.fullmatch(r"[0-9A-F]{64}", expected_input)
            or report.get("inputSetSha256") != expected_input):
        raise ValueError(f"{LABEL}.report:input-set-mismatch")
    if report.get("status") != "complete" or report.get("publicationEligible") is not True:
        raise ValueError(f"{LABEL}.report:incomplete")
    for name in ("buffResidualActionsNativeValidation",):
        if report["provenance"][name]["status"] != "validated":
            raise ValueError(f"{LABEL}.report:{name}-unvalidated")
    if any(row["status"] != "validated" for row in report["provenance"]["buffFrontiersNativeValidation"].values()):
        raise ValueError(f"{LABEL}.report:buff-frontiers-unvalidated")
    native = validate_current_native_contract()
    if native["status"] != "validated":
        raise ValueError(f"{LABEL}.native:{native['status']}:{native.get('detail')}")
    rows = []
    for row in report["files"]:
        candidates = [
            candidate for candidate in row["candidates"]
            if candidate.get("readerAcceptedThroughEof") is True
        ]
        if len(candidates) != 1:
            raise ValueError(f"{LABEL}.report:accepted-candidate-count={len(candidates)}")
        candidate = candidates[0]
        if not candidate.get("namedSchemaReceipt"):
            raise ValueError(f"{LABEL}.report:accepted-candidate-without-named-receipt")
        blocker = candidate["namedSchemaReceipt"]["firstBlocker"]
        if blocker["category"] != "positive-modifier-recursive-proof" or blocker["field"] != "damageModifier":
            continue
        identity = row["identity"]
        source = identity["fileName"]
        if (identity.get("status") != "verified"
                or identity.get("inputSetSha256") != expected_input
                or not re.fullmatch(r"Data/Json/BuffData/[^/\\]+[.]json", source)):
            raise ValueError(f"{LABEL}.report:source-identity:{source}")
        name = Path(source).name
        data = (export_root / name).read_bytes()
        if (len(data) != identity["length"]
                or hashlib.sha256(data).hexdigest().upper() != row["logicalSha256"]):
            raise ValueError(f"{LABEL}.logical-sha256:{source}")
        receipt = decode_damage_modifier_collection(
            data, blocker["start"], blocker["end"], source=source,
            native_validation=native,
        )
        rows.append({"source": source, "logicalSha256": row["logicalSha256"],
                     "receipt": receipt})
    actions = Counter(row["receipt"]["conditionActionUnionCount"] for row in rows)
    processors = Counter(processor["tag"] for row in rows
                         for element in row["receipt"]["elements"]
                         for field in element["fields"] if field["name"] == "damageProcessors"
                         for processor in field["processors"])
    return {"schema": "endfield.buff-damage-modifier-child-receipt.v1",
            "status": "complete", "publicationEligible": False,
            "sourceReport": str(report_path),
            "sourceReportSha256": hashlib.sha256(report_raw).hexdigest().upper(),
            "inputSetSha256": report["inputSetSha256"],
            "nativeValidation": native,
            "summary": {"firstBlockerFiles": len(rows),
                        "childElements": sum(row["receipt"]["count"] for row in rows),
                        "conditionActionUnionCountByFile": dict(sorted(actions.items())),
                        "processorTags": {str(k): v for k, v in sorted(processors.items())},
                        "wholeRecursiveSchemasPromoted": 0},
            "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buff-report", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_first_blockers(
        args.buff_report, args.export_root,
        expected_input_set_sha256=args.expected_input_set_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
