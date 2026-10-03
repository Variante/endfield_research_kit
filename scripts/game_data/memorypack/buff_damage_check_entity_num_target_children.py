"""Selected CheckEntityNum target composition through independently typed children.

The selected parent owns checkTarget and its endpoint. The existing
TargetSettings, DirectionSettings and SelectorData validators independently
name and authenticate the child readers. Only the reached null nested targets,
null finder and empty/null subtype lists are admitted here. A positive body
needs its own proof. This reader admits one stored target only, never a sword
condition, BuffData root or runtime target choice.
"""
from __future__ import annotations

from pathlib import Path
import struct
from typing import Any

from scripts.game_data.memorypack import buff_damage_check_entity_num_child as parent
from scripts.game_data.memorypack import buff_target_settings_child_receipt as target
from scripts.game_data.memorypack import buff_direction_settings_child_receipt as direction
from scripts.game_data.memorypack import buff_selector_data_child_receipt as selector
from scripts.game_data.memorypack.derived_values import ValueReader


SCHEMA = "endfield.buff-damage-check-entity-num-target-children-receipt.v1"
LABEL = "buffDamageCheckEntityNumTargetChildren"


def validate_current_native_contract(audit_report_path: Path, *, gameassembly: Path | None = None,
                                    metadata: Path | None = None, target_parent_tags: tuple[int, ...] | None = None) -> dict[str, Any]:
    """Join the selected parent context to independent target and child gates."""
    paths = {key: value for key, value in (("gameassembly", gameassembly), ("metadata", metadata)) if value is not None}
    parent_native = parent.validate_current_native_contract(audit_report_path, **paths)
    if parent_native.get("status") != "validated":
        return {"status": parent_native.get("status", "failed"),
                "detail": parent_native.get("detail", "parent native gate failed")}
    contract = parent._contract()
    expected = contract["nativeInputs"]
    target_native = target.validate_current_native_contract(parent_tags=target_parent_tags, **paths)
    direction_native = direction.validate_current_native_contract(target_native=target_native, **paths)
    selector_native = selector.validate_current_native_contract(target_native=target_native, **paths)
    if (parent_native.get("nativeInputs") != contract["nativeInputs"]
            or any(row.get("status") != "validated" or row.get("nativeInputs") != expected
                   for row in (target_native, direction_native, selector_native))):
        raise ValueError(f"{LABEL}.native:child-or-build-drift")
    registry = parent_native["_registry"]
    action_plan = registry.plans[parent_native["actionDefinition"]]
    selected = contract["selectedSource"]
    fields = [row for row in action_plan if row.name == selected["targetField"]["name"]]
    if (len(fields) != 1 or fields[0].kind != "object"
            or fields[0].ref != target_native["targetDefinition"]
            or registry.plans[fields[0].ref]
            != target_native["_registry"].plans[target_native["targetDefinition"]]
            or target_native["targetMemberNames"] != contract["targetDirectMemberNames"]):
        raise ValueError(f"{LABEL}.native:parent-target-plan-join")
    return {"status": "validated", "nativeInputs": contract["nativeInputs"],
            "source": selected, "parentNative": parent_native,
            "targetNative": target_native, "directionNative": direction_native,
            "selectorNative": selector_native}


def _null_or_empty_children(data: bytes, child: dict[str, Any], *, kind: str) -> None:
    """Close only reached empty branches, never an unproved positive body."""
    if child.get("status") == "exact-null":
        if child["end"] != child["start"] + 1 or data[child["start"]] != 0xFF:
            raise ValueError(f"{LABEL}.{kind}:null-end")
        return
    if child.get("status") != "named-direct-members-exact-span":
        raise ValueError(f"{LABEL}.{kind}:child-status={child.get('status')}")
    nested = [row for row in child["namedMembers"]
              if row["kind"] in ("object", "union", "list")]
    if kind == "direction":
        if (len(nested) != 2 or any(row["kind"] != "object"
                or row.get("nestedTargetStatus") != "exact-null"
                or row["end"] != row["start"] + 1 or data[row["start"]] != 0xFF
                for row in nested)):
            raise ValueError(f"{LABEL}.direction:positive-or-unproved-nested-target")
    else:
        if len(nested) != 3:
            raise ValueError(f"{LABEL}.selector:member-kinds")
        for row in nested:
            if row["kind"] == "union":
                if (row.get("unionTag") is not None
                        or row["end"] != row["start"] + 1 or data[row["start"]] != 0xFF):
                    raise ValueError(f"{LABEL}.selector:positive-finder")
            elif (row["kind"] != "list" or row.get("count") not in (None, 0)
                  or row["end"] != row["start"] + 4
                  or struct.unpack_from("<i", data, row["start"])[0] not in (-1, 0)):
                raise ValueError(f"{LABEL}.selector:positive-or-unproved-list")


def decode_selected_target_children(data: bytes, *, source: str,
                                    native_validation: dict[str, Any]) -> dict[str, Any]:
    """Reparse the selected action and every target child to the owned endpoint."""
    contract = parent._contract()
    selected = contract["selectedSource"]
    if (native_validation.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native_validation.get("source") != selected
            or any(native_validation.get(name, {}).get("status") != "validated"
                   or native_validation.get(name, {}).get("nativeInputs") != contract["nativeInputs"]
                   for name in ("parentNative", "targetNative", "directionNative", "selectorNative"))):
        raise ValueError(f"{LABEL}.native:unvalidated source={source}")
    native = native_validation["targetNative"]
    registry = native["_registry"]
    plan = registry.plans[native["targetDefinition"]]
    if [row.name for row in plan] != contract["targetDirectMemberNames"]:
        raise ValueError(f"{LABEL}.target:plan-drift source={source}")
    parent_receipt = parent.decode_selected_child(
        data, source=source, native_validation=native_validation["parentNative"],
    )
    owned = selected["targetField"]
    fields = [row for row in parent_receipt["namedFields"] if row["name"] == owned["name"]]
    if (parent_receipt.get("wholeStoredSpanExact") is not True or len(fields) != 1
            or fields[0]["kind"] != "object"
            or (fields[0]["start"], fields[0]["end"]) != (owned["start"], owned["end"])):
        raise ValueError(f"{LABEL}.parent:field-ownership source={source}")
    reader = ValueReader(data, source, owned["end"], registry=registry)
    reader.pos = owned["start"]
    reader.header(len(plan))
    members = []
    for member in plan:
        start = reader.pos
        reader._value_member(member, 1)
        members.append({"fieldName": member.name, "kind": member.kind,
                        "start": start, "end": reader.pos})
    if (reader.pos != owned["end"] or members[0]["start"] != owned["start"] + 1
            or any(a["end"] != b["start"] for a, b in zip(members, members[1:]))):
        raise ValueError(f"{LABEL}.target:end expected={owned['end']} actual={reader.pos} source={source}")
    children = []
    for name, owner, decoder in (
        (direction.FIELD_NAME, "direction", direction.decode_direction_settings_value),
        (selector.FIELD_NAME, "selector", selector.decode_selector_data_value),
    ):
        nested = [row for row in members if row["fieldName"] == name and row["kind"] == "object"]
        if len(nested) != 1:
            raise ValueError(f"{LABEL}.target:typed-child-field={name} source={source}")
        field = nested[0]
        try:
            child = decoder(data, source=source, logical_sha256=selected["sha256"],
                            start=field["start"], end=field["end"],
                            native_validation=native_validation[owner + "Native"])
            _null_or_empty_children(data, child, kind=owner)
        except ValueError as exc:
            raise ValueError(f"{LABEL}.child field={name} source={source} sha256={selected['sha256']} "
                             f"range=[{field['start']},{field['end']}) detail={str(exc)[:500]}") from exc
        children.append({"parentField": name, "receipt": child,
                         "reachedRecursiveStoredSchemaExact": True})
    if {row["fieldName"] for row in members if row["kind"] in ("object", "list", "map", "union", "profile")} != {row["parentField"] for row in children}:
        raise ValueError(f"{LABEL}.target:unowned-nested-field source={source}")
    return {"schema": SCHEMA, "status": "recursive-selected-target-stored-schema",
            "selectedOnly": True, "publicationEligible": False,
            "source": source, "logicalSha256": selected["sha256"],
            "parentTag": parent_receipt["tag"],
            "parentActionRange": [parent_receipt["start"], parent_receipt["end"]],
            "targetField": owned["name"], "start": owned["start"], "end": owned["end"],
            "namedMembers": members, "children": children,
            "wholeTargetStoredSchemaExact": True, "wholeActionRecursiveSchemaExact": False,
            "wholeConditionExact": False, "wholeBuffDataExact": False,
            "evidenceBoundary": (
                "The selected CheckEntityNum owns this TargetSettings extent. Independently "
                "native-gated direct target, direction and selector readers close the reached "
                "stored target, with null nested TargetSettings/finder and empty subtype lists. "
                "Positive interiors, live target choice, condition result, and root source-ID/EOF "
                "admission remain outside this selected child proof."
            )}
