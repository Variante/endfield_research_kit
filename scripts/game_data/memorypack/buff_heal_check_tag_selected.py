"""One source-bound CheckHealTag child inside BuffData.healModifier.

The current Buff outer reader already locates this field. This receipt adds a
native-audited union route, the generated inherited member plan, the nested
query reader and a forward cursor for its condition action. The enclosing
HealModifier and BuffData need the separate processor and root composition.
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
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack import buff_find_settings_child_receipt as query_child
from scripts.game_data.memorypack import buff_damage_sequence_action_condition_receipt as sequence_child
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.buff_root_no_positive_native import (
    validate_current_native_contract as validate_root_native,
)
from scripts.game_data.memorypack.buff_selected_native_audit import validated_action_row


LABEL = "buffHealCheckTagSelected"
SCHEMA = "endfield.buff-heal-check-tag-selected-native-contract.v2"
CONTRACT_PATH = CONTRACTS_DIR / "buff_heal_check_tag_selected_native.json"
ROOT_PATH = CONTRACTS_DIR / "buff_root_no_positive_native.json"
ACTION_PATH = CONTRACTS_DIR / "buff_63_native.json"
QUERY_PATH = query_child.CONTRACT_PATH
SEQUENCE_PATH = sequence_child.CONTRACT_PATH


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL,
    )
    action = value.get("selectedAction") or {}
    plan = action.get("memberPlan") or []
    selected = value.get("selectedSource") or {}
    path = selected.get("path")
    bounds = ("healModifier", "condition", "action", "query", "processor")
    if (
        value.get("reviewedDependencies")
        != [ROOT_PATH.name, ACTION_PATH.name, QUERY_PATH.name, SEQUENCE_PATH.name]
        or not isinstance(path, str)
        or PurePosixPath(path).parts[:3] != ("Data", "Json", "BuffData")
        or len(PurePosixPath(path).parts) != 4
        or not path.endswith(".json")
        or not isinstance(selected.get("sha256"), str)
        or len(selected["sha256"]) != 64
        or any(ch not in "0123456789ABCDEF" for ch in selected["sha256"])
        or type(selected.get("length")) is not int
        or selected["length"] <= 0
        or any(not isinstance(selected.get(key), list)
               or len(selected[key]) != 2
               or any(type(offset) is not int for offset in selected[key])
               or not 0 <= selected[key][0] < selected[key][1] <= selected["length"]
               for key in bounds)
        or not (selected["healModifier"][0] < selected["condition"][0]
                < selected["action"][0] < selected["query"][0]
                < selected["query"][1] == selected["action"][1]
                < selected["condition"][1] < selected["processor"][0]
                < selected["processor"][1] == selected["healModifier"][1])
        or type(action.get("unionTag")) is not int
        or not 0 <= action["unionTag"] <= 65535
        or not isinstance(action.get("wrapperName"), str)
        or not action["wrapperName"]
        or not isinstance(action.get("querySetter"), str)
        or not action["querySetter"].startswith("set___")
        or not isinstance(action.get("queryDeclaredType"), str)
        or not isinstance(action.get("readOrder"), list)
        or len(action["readOrder"]) != 5
        or not isinstance(plan, list) or len(plan) != 5
        or any(not isinstance(row.get("name"), str)
               or not isinstance(row.get("declaredType"), str)
               or not isinstance(row.get("kind"), str)
               or (row.get("width") is not None
                   and (type(row["width"]) is not int or row["width"] <= 0))
               for row in plan)
        or len({row["name"] for row in plan}) != len(plan)
        or plan[-1]["name"] != action["querySetter"].removeprefix("set___").removesuffix("__")
        or plan[-1]["declaredType"] != action["queryDeclaredType"]
        or not isinstance(action.get("queryChildReadOrder"), list)
        or len(action["queryChildReadOrder"]) != 2
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def validate_current_native_contract(audit_report: dict[str, Any]) -> dict[str, Any]:
    """Reuse the current root gate and one previously audited 0x63 route."""
    contract = _contract()
    root, _ = read_reviewed_contract(
        ROOT_PATH, schema="endfield.buff-root-no-positive-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    action = json.loads(ACTION_PATH.read_text(encoding="utf-8"))
    if (
        root.get("nativeInputs") != contract["nativeInputs"]
        or action.get("schemaVersion") != 1
        or action.get("anonymousReadOrder", {}).get("member5")
        != contract["selectedAction"]["readOrder"]
    ):
        raise ValueError(f"{LABEL}.native:dependency-drift")
    root_validation = validate_root_native()
    if root_validation.get("status") != "validated":
        return {"status": root_validation.get("status", "failed"),
                "detail": root_validation.get("detail", "root native gate failed")}
    if root_validation.get("nativeInputs") != contract["nativeInputs"]:
        raise ValueError(f"{LABEL}.native:root-input-drift")
    route = validated_action_row(
        audit_report, expected_inputs=contract["nativeInputs"],
        contract_path=ACTION_PATH, report_key="selectedBuff63ReadOrder",
        union_tag=contract["selectedAction"]["unionTag"],
        wrapper_name=contract["selectedAction"]["wrapperName"],
        read_order_key="member5",
    )
    query_native = query_child.validate_current_native_contract()
    sequence_native = sequence_child.validate_current_native_contract()
    if (query_native.get("status") != "validated"
            or query_native.get("nativeInputs") != contract["nativeInputs"]
            or query_native.get("readOrders", {}).get("query-profile")
            != contract["selectedAction"]["queryChildReadOrder"]
            or sequence_native.get("status") != "validated"):
        raise ValueError(f"{LABEL}.native:nested-read-order")
    selected_sequence, _ = read_reviewed_contract(
        SEQUENCE_PATH, schema="endfield.buff-damage-sequence-action-condition-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    if selected_sequence.get("nativeInputs") != contract["nativeInputs"]:
        raise ValueError(f"{LABEL}.native:sequence-inputs")
    # The audited formatter gives the source read order. Check the selected
    # wrapper's one generated setter before assigning its fifth member a name.
    gate = check_installed_native_inputs(
        contract["nativeInputs"]["GameAssembly.dll"],
        contract["nativeInputs"]["global-metadata.dat"],
    )
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail}
    image = open_native_image(gate.gameassembly, gate.metadata)
    wrapper = contract["selectedAction"]["wrapperName"]
    routes, routes_audit = load_action_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    action_route = routes.get(contract["selectedAction"]["unionTag"])
    plan = contract["selectedAction"]["memberPlan"]
    if (
        routes_audit.get("status") != "validated"
        or action_route is None or action_route.status != "resolved"
        or action_route.wrapper_name != wrapper
        or action_route.inherited_member_count != len(plan) - 1
        or list(action_route.member_order) != [row["name"] for row in plan]
        or list(action_route.member_declared_types)
        != [row["declaredType"] for row in plan]
        or list(action_route.member_kinds) != [row["kind"] for row in plan]
        or list(action_route.member_widths) != [row["width"] for row in plan]
        or sequence_native.get("serializedReadOrder")
        != selected_sequence.get("serializedReadOrder")
        or len(selected_sequence.get("serializedReadOrder") or []) != 3
    ):
        raise ValueError(f"{LABEL}.native:action-member-route")
    owners = [row for row in image.metadata.types
              if image.metadata.type_full_name(row) == wrapper]
    if len(owners) != 1:
        raise ValueError(f"{LABEL}.native:wrapper-count={len(owners)}")
    setters = image.setter_methods(owners[0], parameter="typeName", label=LABEL)
    if (len(setters) != 1
            or setters[0][1:] != [contract["selectedAction"]["querySetter"],
                                  contract["selectedAction"]["queryDeclaredType"]]):
        raise ValueError(f"{LABEL}.native:query-setter")
    image.validate_method_row([setters[0][0], wrapper, *setters[0][1:]], label=LABEL)
    return {
        "status": "validated", "nativeInputs": contract["nativeInputs"],
        "selectedAction": contract["selectedAction"],
        "selectedSource": contract["selectedSource"],
        "root": {"status": "validated", "memberCount": root_validation["memberCount"]},
        "action": route, "queryChild": query_native,
        "sequenceChild": sequence_native,
        "sequenceReadOrder": selected_sequence["serializedReadOrder"],
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_selected_source(data: bytes, *, source: str,
                           native_validation: dict[str, Any],
                           outer_row: dict[str, Any]) -> dict[str, Any]:
    """Advance only the selected field and its 0x63 action on original bytes."""
    contract = _contract()
    selected = contract["selectedSource"]
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("selectedSource") != selected
        or native_validation.get("selectedAction") != contract["selectedAction"]
        or native_validation.get("root", {}).get("status") != "validated"
        or native_validation.get("action", {}).get("status") != "validated"
        or native_validation["action"].get("unionTag")
        != contract["selectedAction"]["unionTag"]
        or native_validation.get("queryChild", {}).get("status") != "validated"
        or native_validation.get("sequenceChild", {}).get("status") != "validated"
    ):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if (
        not isinstance(data, bytes)
        or source != selected["path"]
        or len(data) != selected["length"]
        or hashlib.sha256(data).hexdigest().upper() != selected["sha256"]
    ):
        raise ValueError(f"{LABEL}.source:path-length-or-sha256")
    identity = outer_row.get("identity") or {}
    candidates = outer_row.get("candidates") or []
    if (
        identity.get("fileName") != source
        or identity.get("length") != len(data)
        or outer_row.get("logicalSha256") != selected["sha256"]
        or outer_row.get("coverageStatus") != "unique"
        or outer_row.get("candidateCount") != 1
        or len(candidates) != 1
    ):
        raise ValueError(f"{LABEL}.outer:identity-or-coverage")
    prior = candidates[0].get("namedSchemaReceipt") or {}
    fields = prior.get("forwardNamedFields") or []
    field = fields[13] if len(fields) == 15 else {}
    if (
        prior.get("physicalEof") != len(data)
        or field.get("index") != 13
        or field.get("name") != "healModifier"
        or [field.get("start"), field.get("end")] != selected["healModifier"]
        or field.get("count") != 1
        or field.get("recursiveNamedSchemaExact") is not False
        or {"field": "healModifier", "category": "positive-modifier-recursive-proof",
            "start": selected["healModifier"][0],
            "end": selected["healModifier"][1]} not in (prior.get("blockers") or [])
    ):
        raise ValueError(f"{LABEL}.outer:field-13-drift")

    field_start, field_end = selected["healModifier"]
    reader = Reader(data, source, field_end)
    reader.pos = field_start
    count = reader.heal_modifier_collection_profile()
    if count != 1 or reader.pos != field_end:
        raise ValueError(f"{LABEL}.heal-modifier:count-or-end")
    expected_records = {
        "sequence": (*selected["condition"], None),
        "union": (*selected["action"], contract["selectedAction"]["unionTag"]),
        "anonymous-query-profile": (*selected["query"], None),
        "anonymous-heal-processor-profile": (*selected["processor"], 0),
    }
    for kind, (start, end, tag) in expected_records.items():
        found = [row for row in reader.records
                 if row.get("kind") == kind and row.get("start") == start
                 and row.get("end") == end]
        if len(found) != 1 or (tag is not None
                               and found[0].get("tag", found[0].get("variant")) != tag):
            raise ValueError(f"{LABEL}.cursor:{kind}")

    action_start, action_end = selected["action"]
    query_start, query_end = selected["query"]
    plan = contract["selectedAction"]["memberPlan"]
    query_names = contract["selectedAction"]["queryChildReadOrder"]
    sequence_names = native_validation["sequenceReadOrder"]
    common_width = sum(row["width"] for row in plan[:-1])
    if (
        action_start + 2 + common_width != query_start
        or data[action_start] != contract["selectedAction"]["unionTag"]
        or data[action_start + 1] != len(plan)
        or data[query_start] != len(query_names)
        or data[selected["condition"][0]] != len(sequence_names)
        or struct.unpack_from("<i", data, selected["condition"][0] + 1)[0] != 1
    ):
        raise ValueError(f"{LABEL}.action:member-layout")
    query = Reader(data, source, query_end)
    query.pos = query_start
    query.query_profile()
    if query.pos != query_end:
        raise ValueError(f"{LABEL}.query:end")
    count = struct.unpack_from("<i", data, query_start + 5)[0]
    if count < 0 or query_start + 9 + count * 4 != query_end:
        raise ValueError(f"{LABEL}.query:count")
    members = []
    cursor = action_start + 2
    for member in plan[:-1]:
        width = member["width"]
        members.append({"name": member["name"],
                        "declaredType": member["declaredType"],
                        "kind": member["kind"], "start": cursor,
                        "end": cursor + width,
                        "rawHex": data[cursor:cursor + width].hex().upper()})
        cursor += width
    if cursor != query_start:
        raise ValueError(f"{LABEL}.action:common-end")
    raw_tags = [
        f"{struct.unpack_from('<I', data, query_start + 9 + i * 4)[0]:08X}"
        for i in range(count)
    ]
    query_receipt = {"name": plan[-1]["name"], "start": query_start,
                     "end": query_end, "memberCount": len(query_names),
                     "fields": [
                         {"name": query_names[0], "start": query_start + 1,
                          "end": query_start + 5,
                          "rawBitsHex": data[query_start + 1:query_start + 5].hex().upper()},
                         {"name": query_names[1], "start": query_start + 5,
                          "end": query_end, "count": count,
                          "rawTagBits": raw_tags},
                     ], "wholeStoredSchemaExact": True,
                     "runtimeMeaningObserved": False}
    terminal_start = selected["condition"][1] - 2
    if terminal_start != action_end:
        raise ValueError(f"{LABEL}.condition:terminal-boundary")
    sequence_fields = [
        {"name": sequence_names[0], "start": selected["condition"][0] + 1,
         "end": terminal_start, "count": 1},
        {"name": sequence_names[1], "start": terminal_start,
         "end": terminal_start + 1, "rawByte": data[terminal_start]},
        {"name": sequence_names[2], "start": terminal_start + 1,
         "end": terminal_start + 2, "rawByte": data[terminal_start + 1]},
    ]
    return {
        "schema": "endfield.buff-heal-check-tag-selected-receipt.v2",
        "status": "exact-selected-check-heal-tag-action",
        "source": source, "logicalSha256": selected["sha256"],
        "healModifier": {"start": field_start, "end": field_end,
                         "count": 1, "wholeNamedSchemaExact": False},
        "condition": {"start": selected["condition"][0],
                      "end": selected["condition"][1], "actionCount": 1,
                      "fields": sequence_fields,
                      "wholeNamedSchemaExact": True},
        "action": {"tag": contract["selectedAction"]["unionTag"],
                   "start": action_start, "end": action_end,
                   "wrapperMemberCount": len(plan), "wholeStoredSpanExact": True,
                   "wholeNamedSchemaExact": True,
                   "fields": members + [query_receipt],
                   "query": query_receipt},
        "processor": {"start": selected["processor"][0],
                      "end": selected["processor"][1],
                      "tag": 0, "namedSchemaExact": False},
        "wholeBuffDataExact": False, "publicationEligible": False,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--source", required=True,
                        help="Exact VFS logical path of the selected source")
    parser.add_argument("--audit-report", required=True, type=Path)
    parser.add_argument("--buff-report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    native = validate_current_native_contract(json.loads(args.audit_report.read_text(encoding="utf-8")))
    if native.get("status") != "validated":
        raise SystemExit(f"{LABEL}.native:{native.get('status')}:{native.get('detail', '')}")
    buff_report = json.loads(args.buff_report.read_text(encoding="utf-8"))
    if (buff_report.get("status") != "complete"
            or buff_report.get("publicationEligible") is not True):
        raise SystemExit(f"{LABEL}.outer:report-not-complete")
    matches = [row for row in buff_report.get("files", [])
               if row.get("identity", {}).get("fileName") == args.source]
    if len(matches) != 1:
        raise SystemExit(f"{LABEL}.outer:source-count={len(matches)}")
    result = decode_selected_source(args.input.read_bytes(), source=args.source,
                                    native_validation=native, outer_row=matches[0])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{result['status']} {result['action']['start']}:{result['action']['end']} "
          f"query={result['action']['query']['start']}:{result['action']['query']['end']}")


if __name__ == "__main__":
    main()
