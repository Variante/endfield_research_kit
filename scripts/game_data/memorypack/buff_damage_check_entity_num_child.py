"""Selected sword BuffData CheckEntityNum action and direct TargetSettings members.

The action formatter and TargetSettings generic context come from a prior
validated IL2CPP audit row, rechecked against the installed build and tracked
native contract. The derived plan supplies member names. The original source
SHA and selected action/target endpoints close this one child only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.memorypack.buff_selected_native_audit import validated_action_row
from scripts.game_data.memorypack.derived_plans import load_registry
from scripts.game_data.memorypack.derived_values import ValueReader


LABEL = "buffDamageCheckEntityNumChild"
SCHEMA = "endfield.buff-damage-check-entity-num-child-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-check-entity-num-child-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_check_entity_num_child_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL,
    )
    source = contract.get("selectedSource", {})
    action = source.get("action", {})
    target = source.get("targetField", {})
    dependencies = contract.get("reviewedDependencies")
    path = source.get("path")
    names = contract.get("directMemberNames")
    target_names = contract.get("targetDirectMemberNames")
    if (
        not isinstance(dependencies, list) or len(dependencies) != 3
        or any(not isinstance(name, str) or PurePosixPath(name).name != name
               or not name.endswith(".json") for name in dependencies)
        or not isinstance(path, str)
        or PurePosixPath(path).parts[:3] != ("Data", "Json", "BuffData")
        or len(PurePosixPath(path).parts) != 4 or not path.endswith(".json")
        or not isinstance(source.get("sha256"), str)
        or len(source["sha256"]) != 64
        or any(ch not in "0123456789ABCDEF" for ch in source["sha256"])
        or any(type(action.get(key)) is not int for key in
               ("tag", "start", "end", "memberCount"))
        or not 0 <= action["tag"] <= 255
        or not 0 <= action["start"] < action["end"]
        or not isinstance(names, list) or len(names) != action["memberCount"]
        or len(set(names)) != len(names) or not all(isinstance(x, str) and x for x in names)
        or not isinstance(target_names, list) or not target_names
        or len(set(target_names)) != len(target_names)
        or not all(isinstance(x, str) and x for x in target_names)
        or target.get("name") not in names
        or type(target.get("start")) is not int or type(target.get("end")) is not int
        or not action["start"] + 2 < target["start"] < target["end"] < action["end"]
        or not isinstance(contract.get("wrappedType"), str)
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def validate_current_native_contract(audit_report_path: Path, *,
                                    gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    """Validate the selected formatter audit and generated named member plans."""
    contract = _contract()
    expected = contract["nativeInputs"]
    prior = json.loads((CONTRACTS_DIR / contract["reviewedDependencies"][2]).read_bytes())
    catalog = json.loads((CONTRACTS_DIR / contract["reviewedDependencies"][1]).read_bytes())
    action = contract["selectedSource"]["action"]
    route = [row for row in catalog.get("families", {}).get("AbilityActionData", [])
             if row.get("tag") == action["tag"]]
    if (
        prior.get("nativeInputs") != expected
        or prior.get("selectedSource", {}).get("path") != contract["selectedSource"]["path"]
        or prior.get("selectedSource", {}).get("sha256") != contract["selectedSource"]["sha256"]
        or prior.get("selectedSource", {}).get("nextActionStart") != action["start"]
        or catalog.get("nativeInputs") != {
            "gameAssemblySha256": expected["GameAssembly.dll"],
            "metadataSha256": expected["global-metadata.dat"],
        }
        or len(route) != 1
        or route[0].get("wrappedType") != contract["wrappedType"]
        or route[0].get("memberCount") != action["memberCount"]
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return {"status": gate.status, "detail": gate.detail}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "detail": str(unity)}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "mismatched", "detail": "UnityPlayer.dll hash differs"}
    report = json.loads(Path(audit_report_path).read_bytes())
    selected_native = validated_action_row(
        report, expected_inputs=expected,
        contract_path=CONTRACTS_DIR / contract["reviewedDependencies"][0],
        report_key="selectedBuff61ReadOrder", union_tag=action["tag"],
        wrapper_name=route[0]["wrapperName"], read_order_key="member10",
    )
    if len(selected_native["anonymousReadOrder"]["member10"]) != action["memberCount"]:
        raise ValueError(f"{LABEL}.native:member-read-order")
    registry, plan_audit = load_registry(gameassembly=gate.gameassembly, metadata=gate.metadata)
    if (
        plan_audit.get("status") != "validated"
        or plan_audit.get("nativeInputs", {}).get("GameAssembly.dll", "").upper()
        != expected["GameAssembly.dll"]
        or plan_audit.get("nativeInputs", {}).get("global-metadata.dat", "").upper()
        != expected["global-metadata.dat"]
    ):
        raise ValueError(f"{LABEL}.native:derived-plan-gate")
    definitions = [definition for definition, name in registry.wrapped_names.items()
                   if name == contract["wrappedType"] and definition in registry.plans]
    if len(definitions) != 1:
        raise ValueError(f"{LABEL}.native:action-plan-count={len(definitions)}")
    definition = definitions[0]
    plan = registry.plans[definition]
    target_members = [row for row in plan if row.name == contract["selectedSource"]["targetField"]["name"]]
    if (
        [member.name for member in plan] != contract["directMemberNames"]
        or len(target_members) != 1 or target_members[0].kind != "object"
        or registry.wrapped_names.get(target_members[0].ref)
        != "Beyond.Gameplay.Core.TargetSettings"
        or [member.name for member in registry.plans.get(target_members[0].ref, [])]
        != contract["targetDirectMemberNames"]
    ):
        raise ValueError(f"{LABEL}.native:action-or-target-plan")
    return {
        "status": "validated", "nativeInputs": expected,
        "selectedNative": selected_native, "source": contract["selectedSource"],
        "directMemberNames": contract["directMemberNames"],
        "targetDirectMemberNames": contract["targetDirectMemberNames"],
        "actionDefinition": definition, "_registry": registry,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_selected_child(data: bytes, *, source: str,
                          native_validation: dict[str, Any]) -> dict[str, Any]:
    """Replay the original action and its direct target child to byte 402."""
    contract = _contract()
    selected = contract["selectedSource"]
    action = selected["action"]
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("source") != selected
        or native_validation.get("selectedNative", {}).get("status") != "validated"
        or native_validation.get("selectedNative", {}).get("unionTag") != action["tag"]
        or native_validation.get("directMemberNames") != contract["directMemberNames"]
        or native_validation.get("targetDirectMemberNames")
        != contract["targetDirectMemberNames"]
        or native_validation.get("actionDefinition") is None
        or native_validation.get("_registry") is None
    ):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if (
        not isinstance(data, bytes) or source != selected["path"]
        or hashlib.sha256(data).hexdigest().upper() != selected["sha256"]
        or len(data) < action["end"]
    ):
        raise ValueError(f"{LABEL}.source:path-or-sha256")
    reader = ValueReader(data, source, action["end"], registry=native_validation["_registry"])
    reader.pos = action["start"]
    if reader.take(1, "union-tag") != bytes((action["tag"],)):
        raise ValueError(f"{LABEL}.action:union-tag")
    plan = native_validation["_registry"].plans[native_validation["actionDefinition"]]
    reader.header(action["memberCount"])
    fields = []
    for member in plan:
        field_start = reader.pos
        value = reader._value_member(member, 1)
        fields.append({"name": member.name, "kind": member.kind,
                       "start": field_start, "end": reader.pos, "storedValue": value})
    target_field = next(row for row in fields if row["name"] == selected["targetField"]["name"])
    if (
        reader.pos != action["end"]
        or fields[0]["start"] != action["start"] + 2
        or any(a["end"] != b["start"] for a, b in zip(fields, fields[1:]))
        or (target_field["start"], target_field["end"])
        != (selected["targetField"]["start"], selected["targetField"]["end"])
        or not isinstance(target_field["storedValue"], dict)
        or list(target_field["storedValue"]) != contract["targetDirectMemberNames"]
    ):
        raise ValueError(f"{LABEL}.action:field-or-target-cursor")
    return {
        "schema": SCHEMA, "status": "named-direct-child-exact-span",
        "source": source, "logicalSha256": selected["sha256"],
        "tag": action["tag"], "start": action["start"], "end": action["end"],
        "memberCount": action["memberCount"], "namedFields": fields,
        "targetFieldRange": [target_field["start"], target_field["end"]],
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": False,
        "wholeConditionExact": False, "wholeBuffDataExact": False,
        "evidenceBoundary": native_validation["evidenceBoundary"],
    }
