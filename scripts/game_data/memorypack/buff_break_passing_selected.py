"""Source-bound BuffActionMap receipt for one BreakPassingSmallSceneObject buff.

The selected map contains one SequenceActionData and one four-member action.
Each native dependency is checked against the installed build before assigning
names to the original bytes. This module does not publish corpus coverage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.buff_frontiers_native import load_rows
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_residual_actions import _ResidualReader
from scripts.game_data.memorypack.buff_root_no_positive_native import (
    validate_current_native_contract as validate_root_native,
)


LABEL = "buffBreakPassingSelected"
SCHEMA = "endfield.buff-break-passing-selected-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_break_passing_selected_native.json"
ROOT_PATH = CONTRACTS_DIR / "buff_root_no_positive_native.json"
MAP_PATH = CONTRACTS_DIR / "buff_root_sixth_native.json"
ACTION_PATH = CONTRACTS_DIR / "buff_residual_frontier.json"
SEQUENCE_PATH = CONTRACTS_DIR / "buff_damage_sequence_action_condition_native.json"


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL,
    )
    source = value.get("selectedSource") or {}
    action = value.get("selectedAction") or {}
    path = source.get("path")
    spans = ("buffEventAction", "map", "sequence", "action", "mapEvent")
    if (
        value.get("reviewedDependencies")
        != [ROOT_PATH.name, MAP_PATH.name, ACTION_PATH.name, SEQUENCE_PATH.name]
        or not isinstance(path, str)
        or PurePosixPath(path).parts[:3] != ("Data", "Json", "BuffData")
        or len(PurePosixPath(path).parts) != 4 or not path.endswith(".json")
        or not isinstance(source.get("sha256"), str)
        or len(source["sha256"]) != 64
        or any(ch not in "0123456789ABCDEF" for ch in source["sha256"])
        or type(source.get("length")) is not int or source["length"] <= 0
        or any(not isinstance(source.get(key), list) or len(source[key]) != 2
               or any(type(offset) is not int for offset in source[key])
               or not 0 <= source[key][0] < source[key][1] <= source["length"]
               for key in spans)
        or not (source["buffEventAction"][0] < source["map"][0]
                < source["sequence"][0] < source["action"][0]
                < source["action"][1] < source["sequence"][1]
                == source["mapEvent"][0] < source["mapEvent"][1]
                == source["map"][1] == source["buffEventAction"][1])
        or type(action.get("unionTag")) is not int
        or not 0 <= action["unionTag"] <= 249
        or not isinstance(action.get("wrapperName"), str)
        or len(action.get("memberPlan") or []) != 4
        or any(not isinstance(row.get("name"), str)
               or not isinstance(row.get("kind"), str)
               or type(row.get("width")) is not int or row["width"] <= 0
               for row in action["memberPlan"])
        or len(value.get("mapSetters") or []) != 2
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def _selected_type(image: Any, name: str) -> Any:
    owners = [row for row in image.metadata.types
              if image.metadata.type_full_name(row) == name]
    if len(owners) != 1:
        raise ValueError(f"{LABEL}.native:type={name}; matches={len(owners)}")
    return owners[0]


def validate_current_native_contract() -> dict[str, Any]:
    """Check only the selected root/map/sequence and small residual frontier."""
    contract = _contract()
    root, _ = read_reviewed_contract(
        ROOT_PATH, schema="endfield.buff-root-no-positive-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    action_contract, _ = read_reviewed_contract(
        ACTION_PATH, schema="endfield.buff-residual-frontier-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    sequence, _ = read_reviewed_contract(
        SEQUENCE_PATH,
        schema="endfield.buff-damage-sequence-action-condition-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    map_contract = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    if (root["nativeInputs"] != contract["nativeInputs"]
            or action_contract["nativeInputs"] != contract["nativeInputs"]
            or sequence["nativeInputs"] != contract["nativeInputs"]
            or map_contract.get("schemaVersion") != 1
            or map_contract.get("anonymousReadOrder", {}).get("BuffActionMapHeader2")
            != ["nullable SequenceActionData array", "required raw DWORD"]
            or sequence.get("serializedReadOrder")
            != [row[1].removeprefix("set___").removesuffix("__")
                for row in sequence.get("wrapperSetters", [])]
            or len(sequence.get("serializedReadOrder") or []) != 3):
        raise ValueError(f"{LABEL}.native:dependency-drift")
    root_gate = validate_root_native()
    if root_gate.get("status") != "validated":
        return {"status": root_gate.get("status", "failed"),
                "detail": root_gate.get("detail", "root native gate failed")}
    if root_gate.get("nativeInputs") != contract["nativeInputs"]:
        raise ValueError(f"{LABEL}.native:root-input-drift")
    rows, frontier_audit = load_rows("residual")
    selected_action = rows.get(contract["selectedAction"]["unionTag"])
    if (frontier_audit.get("status") != "validated" or selected_action is None
            or selected_action["wrapperName"]
            != contract["selectedAction"]["wrapperName"]
            or selected_action["serializedMemberCount"] != 4
            or selected_action["generatedOwnFields"] != []
            or selected_action["reachedFile"] != contract["selectedSource"]["path"]
            or selected_action["reachedOffset"] != contract["selectedSource"]["action"][0]):
        raise ValueError(f"{LABEL}.native:action-frontier")
    routes, routes_audit = load_action_routes()
    route = routes.get(contract["selectedAction"]["unionTag"])
    plan = contract["selectedAction"]["memberPlan"]
    if (routes_audit.get("status") != "validated" or route is None
            or route.status != "resolved"
            or route.wrapper_name != selected_action["wrapperName"]
            or route.inherited_member_count != len(plan)
            or list(route.member_order) != [row["name"] for row in plan]
            or list(route.member_kinds) != [row["kind"] for row in plan]
            or list(route.member_widths) != [row["width"] for row in plan]):
        raise ValueError(f"{LABEL}.native:action-member-route")
    gate = check_installed_native_inputs(
        contract["nativeInputs"]["GameAssembly.dll"],
        contract["nativeInputs"]["global-metadata.dat"],
    )
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail}
    image = open_native_image(gate.gameassembly, gate.metadata)
    for row in map_contract["methods"] + sequence["sequenceMethods"]:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(map_contract["codeWindows"] + sequence["sequenceCodeWindows"],
                        label=LABEL)
    image.check_instruction_windows(sequence["sequenceInstructionWindows"], label=LABEL)
    map_owner = map_contract["methods"][1][1]
    setters = contract["mapSetters"]
    if image.setter_methods(_selected_type(image, map_owner), parameter="typeName",
                            label=LABEL) != [row[:3] for row in setters]:
        raise ValueError(f"{LABEL}.native:map-setters")
    for row in setters:
        image.validate_method_row([row[0], map_owner, row[1], row[3]], label=LABEL)
    sequence_owner = sequence["wrapperType"]
    if image.setter_methods(_selected_type(image, sequence_owner),
                            parameter="typeName", label=LABEL) != sequence["wrapperSetters"]:
        raise ValueError(f"{LABEL}.native:sequence-setters")
    context = map_contract["nestedContexts"][1]
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    spec = list(struct.unpack("<iii", image.pe.bytes_at_va(
        int(image.registration["methodSpecs"], 16) + index * 12, 12,
    )))
    args = image.instantiations.resolve(spec[2]).arguments
    if (index != context["methodSpecIndex"] or spec != context["methodSpec"]
            or len(args) != 1 or args[0].raw_type_record_hex != context["argumentRawHex"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]):
        raise ValueError(f"{LABEL}.native:map-sequence-context")
    return {"status": "validated", "nativeInputs": contract["nativeInputs"],
            "selectedSource": contract["selectedSource"],
            "selectedAction": contract["selectedAction"],
            "root": root_gate,
            "mapReadOrder": [row[1].removeprefix("set___").removesuffix("__")
                             for row in setters],
            "sequenceReadOrder": sequence["serializedReadOrder"],
            "evidenceBoundary": contract["evidenceBoundary"]}


def decode_selected_source(data: bytes, *, source: str,
                           native_validation: dict[str, Any],
                           outer_row: dict[str, Any]) -> dict[str, Any]:
    contract = _contract()
    selected = contract["selectedSource"]
    action = contract["selectedAction"]
    if (native_validation.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native_validation.get("selectedSource") != selected
            or native_validation.get("selectedAction") != action
            or native_validation.get("root", {}).get("status") != "validated"
            or native_validation.get("mapReadOrder")
            != [row[1].removeprefix("set___").removesuffix("__")
                for row in contract["mapSetters"]]
            or len(native_validation.get("sequenceReadOrder") or []) != 3):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if (not isinstance(data, bytes) or source != selected["path"]
            or len(data) != selected["length"]
            or hashlib.sha256(data).hexdigest().upper() != selected["sha256"]):
        raise ValueError(f"{LABEL}.source:path-length-or-sha256")
    identity = outer_row.get("identity") or {}
    candidates = outer_row.get("candidates") or []
    prior = (candidates[0].get("namedSchemaReceipt") or {}) if len(candidates) == 1 else {}
    fields = prior.get("forwardNamedFields") or []
    field = fields[5] if len(fields) == 15 else {}
    if (identity.get("fileName") != source or identity.get("length") != len(data)
            or outer_row.get("logicalSha256") != selected["sha256"]
            or outer_row.get("coverageStatus") != "unique"
            or outer_row.get("candidateCount") != 1
            or prior.get("physicalEof") != len(data)
            or field.get("index") != 5 or field.get("name") != "buffEventAction"
            or [field.get("start"), field.get("end")] != selected["buffEventAction"]
            or field.get("recursiveNamedSchemaExact") is not False
            or {"field": "buffEventAction", "category": "anonymous-action-interior",
                "start": selected["buffEventAction"][0],
                "end": selected["buffEventAction"][1]} not in (prior.get("blockers") or [])):
        raise ValueError(f"{LABEL}.outer:field-five-drift")
    start, end = selected["buffEventAction"]
    reader = _ResidualReader(data, source, end)
    reader.pos = start
    reader.buff_action_map_collection_profile()
    expected = {
        "anonymous-buff-action-map-collection-profile": (*selected["buffEventAction"], None),
        "anonymous-buff-action-map-profile": (*selected["map"], None),
        "sequence": (*selected["sequence"], None),
        "union": (*selected["action"], action["unionTag"]),
    }
    if reader.pos != end or len(reader.records) != len(expected):
        raise ValueError(f"{LABEL}.cursor:field-end-or-record-count")
    for kind, (a, z, tag) in expected.items():
        found = [row for row in reader.records if row.get("kind") == kind
                 and row.get("start") == a and row.get("end") == z]
        if len(found) != 1 or (tag is not None and found[0].get("tag") != tag):
            raise ValueError(f"{LABEL}.cursor:{kind}")
    field_count = struct.unpack_from("<i", data, start)[0]
    map_start, _ = selected["map"]
    sequence_start, sequence_end = selected["sequence"]
    action_start, action_end = selected["action"]
    if (field_count != 1 or data[map_start] != len(native_validation["mapReadOrder"])
            or struct.unpack_from("<i", data, map_start + 1)[0] != 1
            or data[sequence_start] != len(native_validation["sequenceReadOrder"])
            or struct.unpack_from("<i", data, sequence_start + 1)[0] != 1
            or data[action_start] != action["unionTag"]
            or data[action_start + 1] != len(action["memberPlan"])
            or action_end + 2 != sequence_end
            or sequence_end != selected["mapEvent"][0]
            or selected["mapEvent"][1] - selected["mapEvent"][0] != 4):
        raise ValueError(f"{LABEL}.cursor:headers-or-counts")
    members = []
    cursor = action_start + 2
    for member in action["memberPlan"]:
        width = member["width"]
        members.append({"name": member["name"], "kind": member["kind"],
                        "start": cursor, "end": cursor + width,
                        "rawHex": data[cursor:cursor + width].hex().upper()})
        cursor += width
    if cursor != action_end:
        raise ValueError(f"{LABEL}.action:member-end")
    sequence_names = native_validation["sequenceReadOrder"]
    return {
        "schema": "endfield.buff-break-passing-selected-receipt.v1",
        "status": "exact-selected-buff-event-action",
        "source": source, "logicalSha256": selected["sha256"],
        "buffEventAction": {"start": start, "end": end, "count": 1,
                            "wholeNamedSchemaExact": True},
        "map": {"start": map_start, "end": selected["map"][1],
                "memberNames": native_validation["mapReadOrder"],
                "event": {"name": native_validation["mapReadOrder"][1],
                          "range": selected["mapEvent"],
                          "rawBitsHex": data[sequence_end:selected["mapEvent"][1]].hex().upper()},
                "wholeNamedSchemaExact": True},
        "sequence": {"start": sequence_start, "end": sequence_end,
                     "memberNames": sequence_names,
                     "fields": [
                         {"name": sequence_names[0], "range": [sequence_start + 1,
                                                               action_end], "count": 1},
                         {"name": sequence_names[1], "range": [action_end,
                                                               action_end + 1],
                          "rawByte": data[action_end]},
                         {"name": sequence_names[2], "range": [action_end + 1,
                                                               sequence_end],
                          "rawByte": data[action_end + 1]},
                     ], "wholeNamedSchemaExact": True},
        "action": {"tag": action["unionTag"], "start": action_start,
                   "end": action_end, "wrapperName": action["wrapperName"],
                   "fields": members, "wholeNamedSchemaExact": True},
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
    print(result["status"], result["buffEventAction"]["start"],
          result["buffEventAction"]["end"])


if __name__ == "__main__":
    main()
