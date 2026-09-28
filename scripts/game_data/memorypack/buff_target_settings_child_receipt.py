"""Selected-build direct TargetSettings members inside named Buff actions.

Each parent adapter replays its complete action and certifies a bounded target
field. The selected derived plan and native TargetSettings reader then name the
thirteen direct stored members. Nested direction and selector bodies retain
their existing structural tier; no runtime targeting is inferred.

Composed parents: ``CreateBuffAction``, ``EffectAction``,
``FinishBuffAdvanced`` and ``ModifyDynamicBlackboard``. The direct stored
order is ``advancedDirection``, ``centerContextKey``, ``centerToGround``,
``centerType``, ``enableAdvancedDirection``, ``ownerContextKey``,
``selectorData``, ``selectorDirection``, ``selectorOwner``, ``target``,
``targetContextKey``, ``targetGroupKey`` and ``targetSource``. Each parent
action is reparsed before its target fields are admitted, and the child
reader must end at that exact field boundary. Null and malformed target
branches fail closed. ``advancedDirection`` and ``selectorData`` are named
one level further by ``buff_direction_settings_child_receipt`` and
``buff_selector_data_child_receipt``; this receipt does not establish their
recursive ownership, live target selection, or a whole BuffData schema.
"""
from __future__ import annotations

from typing import Any, Callable

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack import buff_create_buff_action_receipt as create
from scripts.game_data.memorypack import buff_effect_action_receipt as effect
from scripts.game_data.memorypack import buff_finish_buff_advanced_action_receipt as finish
from scripts.game_data.memorypack import buff_modify_dynamic_blackboard_action_receipt as modify
from scripts.game_data.memorypack.derived_plans import load_registry
from scripts.game_data.memorypack.derived_values import ValueReader


SCHEMA = "endfield.buff-target-settings-action-child-receipt.v1"
LABEL = "buffTargetSettingsActionChild"
TARGET_TYPE = "Beyond.Gameplay.Core.TargetSettings"
TARGET_WRAPPER = "Beyond.MemoryPack.Beyond_Gameplay_Core_TargetSettingsForMemoryPack"
_PARENTS: dict[int, tuple[Callable[..., dict[str, Any]], Callable[..., dict[str, Any]]]] = {
    create.TAG: (create.validate_current_native_contract, create.decode_create_buff_action_receipt),
    effect.TAG: (effect.validate_current_native_contract, effect.decode_effect_action_receipt),
    finish.TAG: (finish.validate_current_native_contract, finish.decode_finish_buff_advanced_action_receipt),
    modify.TAG: (modify.validate_current_native_contract, modify.decode_modify_dynamic_blackboard_action_receipt),
}


def _setter_name(row: list[Any] | tuple[Any, ...]) -> str:
    name = row[1]
    if not isinstance(name, str) or not name.startswith("set___") or not name.endswith("__"):
        raise ValueError(f"{LABEL}.native:setter-name")
    return name.removeprefix("set___").removesuffix("__")


def _bindings(tag: int, audit: dict[str, Any]) -> list[dict[str, str]]:
    """Select only parent fields whose checked native type is TargetSettings."""
    if tag == create.TAG:
        contract = create._create_buff_contract()
        rows = [row for row in contract["wrapper"]["setterMethods"]
                if row[-1] == TARGET_TYPE]
        bindings = [{"fieldName": _setter_name(row), "kind": "TargetSettings"}
                    for row in rows]
        schema = create.SCHEMA
    elif tag == finish.TAG:
        contract = finish._contract()
        setters = (contract["wrapper"]["inheritedSetterMethods"]
                   + contract["wrapper"]["setterMethods"])
        bindings = [{"fieldName": _setter_name(row), "kind": kind}
                    for row, kind in zip(setters, contract["orderedReadKinds"], strict=True)
                    if row[-1] == TARGET_TYPE and kind == "target-profile"]
        schema = finish.SCHEMA
    elif tag in (effect.TAG, modify.TAG):
        parent = effect if tag == effect.TAG else modify
        source, _catalog = parent._contracts()
        names, kinds = audit["memberNames"], audit["readKinds"]
        nested_kinds = parent._NESTED_PROFILE_KINDS
        top_nested = [(name, kind) for name, kind in zip(names, kinds, strict=True)
                      if kind in nested_kinds]
        contexts = source["nestedContexts"][:len(top_nested)]
        if len(contexts) != len(top_nested):
            raise ValueError(f"{LABEL}.native:parent-context-count={tag:#x}")
        bindings = [{"fieldName": name, "kind": kind}
                    for (name, kind), context in zip(top_nested, contexts, strict=True)
                    if context["typeName"] == TARGET_TYPE
                    and kind in ("target-profile", "member13")]
        schema = parent.SCHEMA
    else:
        raise ValueError(f"{LABEL}.native:unsupported-parent-tag={tag:#x}")
    if not bindings or len({row["fieldName"] for row in bindings}) != len(bindings):
        raise ValueError(f"{LABEL}.native:missing-or-duplicate-target={tag:#x}")
    return [dict(row, parentSchema=schema) for row in bindings]


def validate_current_native_contract() -> dict[str, Any]:
    """Gate the selected target reader, generated plan and four parent joins."""
    inputs = create._create_buff_contract()["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["GameAssembly.dll"], inputs["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    registry, plan_audit = load_registry(
        gameassembly=gate.gameassembly, metadata=gate.metadata
    )
    if (plan_audit.get("status") != "validated"
            or plan_audit.get("nativeInputs", {}).get("GameAssembly.dll", "").upper()
            != inputs["GameAssembly.dll"]
            or plan_audit.get("nativeInputs", {}).get("global-metadata.dat", "").upper()
            != inputs["global-metadata.dat"]):
        raise ValueError(f"{LABEL}.native:derived-plan-drift")
    definitions = [definition for definition, name in registry.wrapped_names.items()
                   if name == TARGET_TYPE and definition in registry.plans]
    if len(definitions) != 1:
        raise ValueError(f"{LABEL}.native:target-plan-count={len(definitions)}")
    definition = definitions[0]
    plan = registry.plans[definition]
    source, _catalog = modify._contracts()
    if len(plan) != len(source["anonymousReadOrder"]["member13"]):
        raise ValueError(f"{LABEL}.native:target-member-count")
    image = open_native_image(gate.gameassembly, gate.metadata)
    target_rows = [row for row in source["methods"] if row[1] == TARGET_WRAPPER]
    if len(target_rows) != 1:
        raise ValueError(f"{LABEL}.native:target-reader-count={len(target_rows)}")
    image.validate_method_row(target_rows[0], label=LABEL)
    image.check_windows(source["codeWindows"], label=LABEL)
    owners = [row for row in image.metadata.types
              if image.metadata.type_full_name(row) == TARGET_WRAPPER]
    if len(owners) != 1:
        raise ValueError(f"{LABEL}.native:target-wrapper-count={len(owners)}")
    setters = image.setter_methods(owners[0], parameter="typeName", label=LABEL)
    names = [_setter_name(row) for row in setters]
    if names != [member.name for member in plan]:
        raise ValueError(f"{LABEL}.native:target-setter-order")
    parent_native = {}
    bindings = {}
    for tag, (validator, _decoder) in _PARENTS.items():
        audit = validator()
        if (audit.get("status") != "validated"
                or audit.get("unionTag") != tag
                or any(audit.get("nativeInputs", {}).get(name) != inputs[name]
                       for name in ("GameAssembly.dll", "global-metadata.dat"))):
            raise ValueError(f"{LABEL}.native:parent-{tag:#x}-drift")
        parent_native[tag] = audit
        bindings[tag] = _bindings(tag, audit)
    return {
        "status": "validated", "nativeInputs": inputs,
        "targetDefinition": definition, "targetMemberNames": names,
        "planAudit": {"status": plan_audit["status"],
                      "nativeInputs": plan_audit["nativeInputs"]},
        "parentNative": parent_native, "bindings": bindings,
        "_registry": registry,
    }


def decode_target_settings_action_child_receipt(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    tag: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Reparse a certified action and name each directly stored target member."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}:native-not-validated")
    if tag not in _PARENTS or tag not in native_validation.get("bindings", {}):
        raise ValueError(f"{LABEL}:unsupported-parent-tag={tag:#x}")
    _validator, decoder = _PARENTS[tag]
    parent = decoder(
        data, source=source, logical_sha256=logical_sha256,
        start=start, end=end, native_validation=native_validation["parentNative"][tag],
    )
    bindings = native_validation["bindings"][tag]
    if (
        parent.get("status") != "named-wrapper-exact-span"
        or parent.get("schema") != bindings[0]["parentSchema"]
        or parent.get("tag") != tag
        or parent.get("source") != source
        or parent.get("logicalSha256") != logical_sha256.upper()
        or parent.get("start") != start or parent.get("end") != end
        or parent.get("wholeActionByteSpanExact") is not True
    ):
        raise ValueError(f"{LABEL}:parent-receipt-drift")
    registry = native_validation["_registry"]
    definition = native_validation["targetDefinition"]
    plan = registry.plans[definition]
    if [member.name for member in plan] != native_validation["targetMemberNames"]:
        raise ValueError(f"{LABEL}:target-plan-drift")
    children = []
    seen = set()
    for binding in bindings:
        fields = [field for field in parent["namedFields"]
                  if field["fieldName"] == binding["fieldName"]
                  and field["kind"] == binding["kind"]]
        if len(fields) != 1 or binding["fieldName"] in seen:
            raise ValueError(f"{LABEL}:parent-target-field-missing-or-ambiguous")
        seen.add(binding["fieldName"])
        field = fields[0]
        reader = ValueReader(data, source, field["end"], registry=registry)
        reader.pos = field["start"]
        if reader.peek() == 0xFF:
            reader.take(1, "null-target-settings")
            members = []
            status = "exact-null"
        else:
            reader.header(len(plan))
            members = []
            for member in plan:
                member_start = reader.pos
                reader._value_member(member, 1)
                if reader.pos <= member_start:
                    raise ValueError(f"{LABEL}:target-member-no-progress:{member.name}")
                members.append({"fieldName": member.name, "kind": member.kind,
                                "start": member_start, "end": reader.pos,
                                "nestedBodyStructural": member.kind in ("object", "list", "map", "union", "profile")})
            status = "named-direct-members-exact-span"
        if reader.pos != field["end"] or (members and members[-1]["end"] != field["end"]):
            raise ValueError(f"{LABEL}:target-end={reader.pos}; expected={field['end']}")
        children.append({"parentField": binding["fieldName"],
                         "start": field["start"], "end": field["end"],
                         "status": status, "memberCount": len(members) if members else None,
                         "namedMembers": members, "wholeStoredSpanExact": True,
                         "recursiveNamedSchemaExact": False})
    return {
        "schema": SCHEMA, "status": "named-direct-target-members",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "parentTag": tag, "parentActionRange": [start, end],
        "targetChildren": children, "wholeActionRecursiveSchemaExact": False,
        "wholeBuffDataExact": False,
        "evidenceBoundary": (
            "Selected parent readers and generated field setters establish target "
            "ownership and exact child extents. The selected TargetSettings plan "
            "names thirteen direct stored members. Direction and selector subtrees "
            "retain structural evidence; runtime target selection and enclosing "
            "BuffData recursive naming remain unresolved."
        ),
    }
