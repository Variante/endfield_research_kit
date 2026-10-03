"""Source-bound prefix of the selected sword BuffData damage condition.

This closes only the first two actions. The FindTarget decoder is reused for
its bounded byte grammar, but its native authority comes from the separate
current-build Buff audit receipt checked here, not from a SkillData timeline.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_damage_check_type_mask_condition_receipt as mask
from scripts.game_data.memorypack.buff_selected_native_audit import validated_action_row
from scripts.game_data.memorypack import skill_timeline_find_target as find_target


LABEL = "buffDamageSwordConditionPrefix"
SCHEMA = "endfield.buff-damage-sword-condition-prefix-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-sword-condition-prefix-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_sword_condition_prefix_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL,
    )
    source = contract.get("selectedSource", {})
    actions = source.get("selectedActions", [])
    dependencies = contract.get("reviewedDependencies")
    source_path = source.get("path")
    routes = contract.get("selectedFindTargetRoutes", {})
    if (
        not isinstance(dependencies, list) or len(dependencies) != 3
        or any(not isinstance(name, str) or PurePosixPath(name).name != name
               or not name.endswith("_native.json") for name in dependencies)
        or not isinstance(source_path, str)
        or PurePosixPath(source_path).parts[:3] != ("Data", "Json", "BuffData")
        or len(PurePosixPath(source_path).parts) != 4
        or not source_path.endswith(".json")
        or not isinstance(source.get("sha256"), str)
        or len(source["sha256"]) != 64
        or any(ch not in "0123456789ABCDEF" for ch in source["sha256"])
        or type(source.get("conditionStart")) is not int
        or type(source.get("actionCount")) is not int
        or source["actionCount"] <= 2
        or not isinstance(actions, list) or len(actions) != 2
        or any(type(action.get(key)) is not int for action in actions
               for key in ("tag", "start", "end"))
        or not (0 <= source["conditionStart"] < actions[0]["start"] < actions[0]["end"]
                == actions[1]["start"] < actions[1]["end"]
                == source.get("nextActionStart"))
        or actions[0]["start"] != source["conditionStart"] + 5
        or not isinstance(routes, dict)
        or any(not isinstance(routes.get(kind), dict) for kind in
               ("finder", "validator", "postProcessor"))
        or len(routes["finder"]) != 1 or len(routes["validator"]) != 1
        or routes["postProcessor"] != {}
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def _validated_b2_audit(report: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    """Consume the existing audited native proof without rerunning its sweep."""
    selected_tag = contract["selectedSource"]["selectedActions"][1]["tag"]
    catalog = json.loads((CONTRACTS_DIR / "levelscript_union_tags.json").read_bytes())
    catalog_route = [row for row in catalog.get("families", {}).get("AbilityActionData", [])
                     if row.get("tag") == selected_tag]
    if len(catalog_route) != 1 or selected_tag != find_target.find_target_plain_tag():
        raise ValueError(f"{LABEL}.audit:b2-dispatcher-route")
    try:
        return validated_action_row(
            report, expected_inputs=contract["nativeInputs"],
            contract_path=CONTRACTS_DIR / contract["reviewedDependencies"][1],
            report_key="selectedBuffB2ReadOrder", union_tag=selected_tag,
            wrapper_name=catalog_route[0]["wrapperName"], read_order_key="actionMember18",
        )
    except ValueError as exc:
        raise ValueError(f"{LABEL}.audit:{exc}") from exc


def validate_current_native_contract(audit_report_path: Path, *,
                                    gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    """Require the current native gate and the selected Buff B2 audit receipt."""
    contract = _contract()
    expected = contract["nativeInputs"]
    mask_contract = json.loads((CONTRACTS_DIR / contract["reviewedDependencies"][0]).read_bytes())
    skill_contract = json.loads((CONTRACTS_DIR / contract["reviewedDependencies"][2]).read_bytes())
    if (
        mask_contract.get("nativeInputs") != expected
        or skill_contract.get("nativeInputs") != expected
        or skill_contract.get("dependencies", [{}])[0].get("path")
        != contract["reviewedDependencies"][1]
        or any(skill_contract.get("selectedSubtypeRoutes", {}).get(kind, {}).get(tag) != name
               for kind, rows in contract["selectedFindTargetRoutes"].items()
               for tag, name in rows.items())
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
    # The existing mask validator gates all three installed binaries and its
    # dispatcher, source reads, enum contexts and enclosing sequence reader.
    selected_mask = mask.validate_current_native_contract(gameassembly=gameassembly, metadata=metadata)
    if selected_mask.get("status") != "validated":
        return {"status": selected_mask.get("status", "failed"),
                "detail": selected_mask.get("detail", "mask native gate failed")}
    if (
        selected_mask.get("nativeInputs") != expected
        or selected_mask.get("unionTag") != contract["selectedSource"]["selectedActions"][0]["tag"]
        or selected_mask.get("sequenceMemberCount") != 3
        or selected_mask.get("sequenceTerminalByteCount") != 2
    ):
        raise ValueError(f"{LABEL}.native:mask-or-sequence-drift")
    report = json.loads(Path(audit_report_path).read_bytes())
    selected_b2 = _validated_b2_audit(report, contract)
    return {
        "status": "validated", "nativeInputs": expected,
        "mask": selected_mask, "findTarget": selected_b2,
        "source": contract["selectedSource"],
        "selectedFindTargetRoutes": contract["selectedFindTargetRoutes"],
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_selected_prefix(data: bytes, *, source: str,
                           native_validation: dict[str, Any]) -> dict[str, Any]:
    """Replay only the first two actions on the selected original source."""
    contract = _contract()
    selected = contract["selectedSource"]
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("source") != selected
        or native_validation.get("mask", {}).get("status") != "validated"
        or native_validation.get("mask", {}).get("actionMemberPlan")
        != json.loads((CONTRACTS_DIR / contract["reviewedDependencies"][0]).read_bytes())[
            "actionMemberPlan"]
        or native_validation.get("findTarget", {}).get("status") != "validated"
        or native_validation.get("findTarget", {}).get("unionTag")
        != selected["selectedActions"][1]["tag"]
        or native_validation.get("selectedFindTargetRoutes")
        != contract["selectedFindTargetRoutes"]
    ):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if (
        not isinstance(data, bytes)
        or source != selected["path"]
        or hashlib.sha256(data).hexdigest().upper() != selected["sha256"]
        or len(data) < selected["nextActionStart"]
    ):
        raise ValueError(f"{LABEL}.source:path-or-sha256")
    start = selected["conditionStart"]
    end = selected["nextActionStart"]
    reader = Reader(data, source, end)
    reader.pos = start
    reader.header(native_validation["mask"]["sequenceMemberCount"])
    action_count = reader.count(1, reserve=2, nullable=True)
    if action_count != selected["actionCount"] or reader.pos != selected["selectedActions"][0]["start"]:
        raise ValueError(f"{LABEL}.sequence:header-or-count")
    mask_start = reader.pos
    mask_tag = selected["selectedActions"][0]["tag"]
    if reader.nested_union_tag((mask_tag,), "condition-action") != mask_tag or reader.peek() == 0xFF:
        raise ValueError(f"{LABEL}.mask:non-null-route")
    plan = native_validation["mask"]["actionMemberPlan"]
    reader.header(len(plan))
    fields = []
    for member in plan:
        field_start = reader.pos
        raw = reader.take(member["width"], member["name"])
        fields.append({"name": member["name"], "declaredType": member["declaredType"],
                       "kind": member["kind"], "start": field_start,
                       "end": reader.pos, "rawHex": raw.hex().upper()})
    if reader.pos != selected["selectedActions"][0]["end"]:
        raise ValueError(f"{LABEL}.mask:cursor={reader.pos}")
    mask_action = {"tag": mask_tag, "start": mask_start, "end": reader.pos,
                   "memberCount": len(plan), "namedFields": fields,
                   "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True}
    find_start = reader.pos
    find_action, find_end = find_target._decode_find_target(data, find_start, end)
    if (
        find_end != selected["selectedActions"][1]["end"]
        or find_action.get("memberCount") != 18
        or find_action.get("fields", {}).get("selectorData", {}).get("finderData", {}).get("subtype")
        != next(iter(contract["selectedFindTargetRoutes"]["finder"].values()))
        or [item.get("subtype") for item in find_action["fields"]["selectorData"]["validatorData"]]
        != list(contract["selectedFindTargetRoutes"]["validator"].values())
        or find_action["fields"]["selectorData"]["postProcessorData"] != []
    ):
        raise ValueError(f"{LABEL}.findTarget:selected-route-or-cursor")
    return {
        "schema": SCHEMA, "status": "exact-selected-condition-prefix",
        "source": source, "logicalSha256": selected["sha256"],
        "conditionStart": start, "actionCount": action_count,
        "prefixStart": selected["selectedActions"][0]["start"],
        "prefixEnd": find_end, "actions": [mask_action, find_action],
        "remainingTopLevelActions": action_count - 2,
        "wholeConditionExact": False, "wholeBuffDataExact": False,
        "evidenceBoundary": native_validation["evidenceBoundary"],
    }
