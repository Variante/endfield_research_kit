"""Named stored members of BlackboardDouble inside selected Buff actions.

The parent action adapters establish an exact wrapper field and physical span.
The independently reviewed addingCooldown child establishes the shared
BlackboardDouble member-three reader and generated setter order. This adapter
composes those proofs without evaluating a runtime blackboard value.
"""
from __future__ import annotations

from typing import Any, Callable

from scripts.game_data.memorypack import buff_adding_cooldown as child
from scripts.game_data.memorypack import buff_create_buff_action_receipt as create
from scripts.game_data.memorypack import buff_finish_buff_advanced_action_receipt as finish
from scripts.game_data.memorypack import buff_modify_dynamic_blackboard_action_receipt as modify
from scripts.game_data.memorypack import buff_raise_train_level_event_receipt as raise_event


SCHEMA = "endfield.buff-blackboard-double-action-child-receipt.v1"
LABEL = "buffBlackboardDoubleActionChild"
DOUBLE_TYPE = "Beyond.Blackboard+BlackboardDouble"
_PARENTS: dict[int, tuple[Callable[..., dict[str, Any]], Callable[..., dict[str, Any]]]] = {
    create.TAG: (create.validate_current_native_contract, create.decode_create_buff_action_receipt),
    finish.TAG: (finish.validate_current_native_contract, finish.decode_finish_buff_advanced_action_receipt),
    modify.TAG: (modify.validate_current_native_contract, modify.decode_modify_dynamic_blackboard_action_receipt),
    raise_event.TAG: (raise_event.validate_current_native_contract, raise_event.decode_raise_train_level_event_receipt),
}


def _setter_name(row: list[Any]) -> str:
    name = row[1]
    if not isinstance(name, str) or not name.startswith("set___") or not name.endswith("__"):
        raise ValueError(f"{LABEL}.contract:setter-name")
    return name.removeprefix("set___").removesuffix("__")


def _binding(tag: int, parent_native: dict[str, Any]) -> dict[str, str]:
    """Derive field identity and wire kind from each reviewed parent route."""
    if tag == create.TAG:
        contract = create._create_buff_contract()
        rows = [row for row in contract["wrapper"]["setterMethods"]
                if row[-1] == DOUBLE_TYPE]
        if len(rows) != 1:
            raise ValueError(f"{LABEL}.native:create-double-setter-count")
        return {"fieldName": _setter_name(rows[0]), "kind": "BlackboardDouble",
                "parentSchema": create.SCHEMA}
    if tag == finish.TAG:
        contract = finish._contract()
        setters = (contract["wrapper"]["inheritedSetterMethods"]
                   + contract["wrapper"]["setterMethods"])
        rows = [(row, kind) for row, kind in zip(
            setters, contract["orderedReadKinds"], strict=True
        ) if row[-1] == DOUBLE_TYPE]
        if len(rows) != 1 or rows[0][1] != "scalar-payload":
            raise ValueError(f"{LABEL}.native:finish-double-source")
        return {"fieldName": _setter_name(rows[0][0]), "kind": rows[0][1],
                "parentSchema": finish.SCHEMA}
    if tag in (modify.TAG, raise_event.TAG):
        if tag == modify.TAG:
            source, _catalog = modify._contracts()
            nested_kinds = modify._NESTED_PROFILE_KINDS
            schema = modify.SCHEMA
        else:
            source, _catalog = raise_event._contracts()
            nested_kinds = {"paired-payload", "scalar-payload"}
            schema = raise_event.SCHEMA
        names = parent_native["memberNames"]
        kinds = parent_native["readKinds"]
        top_nested = [(name, kind) for name, kind in zip(names, kinds, strict=True)
                      if kind in nested_kinds]
        contexts = source["nestedContexts"][:len(top_nested)]
        if len(contexts) != len(top_nested):
            raise ValueError(f"{LABEL}.native:nested-context-count")
        nested = [(name, kind, context["typeName"])
                  for (name, kind), context in zip(top_nested, contexts, strict=True)]
        rows = [(name, kind) for name, kind, type_name in nested
                if type_name == DOUBLE_TYPE]
        if len(rows) != 1 or rows[0][1] != "scalar-payload":
            raise ValueError(f"{LABEL}.native:double-context-route")
        return {"fieldName": rows[0][0], "kind": rows[0][1],
                "parentSchema": schema}
    raise ValueError(f"{LABEL}.native:unsupported-parent-tag={tag:#x}")


def validate_current_native_contract() -> dict[str, Any]:
    """Gate the common child and four exact parent field owners."""
    child_native = child.validate_current_native_contract()
    if child_native.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:child-{child_native.get('status')}")
    child_contract = child._contract()
    inputs = child_contract["nativeInputs"]
    if child_native.get("selectedReadOrder") != child_contract["selectedReadOrder"]:
        raise ValueError(f"{LABEL}.native:child-setter-order")
    bindings = {}
    parent_native = {}
    for tag, (validator, _decoder) in _PARENTS.items():
        audit = validator()
        if (audit.get("status") != "validated"
                or audit.get("unionTag") != tag
                or any(audit.get("nativeInputs", {}).get(name) != inputs[name]
                       for name in ("GameAssembly.dll", "global-metadata.dat"))):
            raise ValueError(f"{LABEL}.native:parent-{tag:#x}-drift")
        bindings[tag] = _binding(tag, audit)
        parent_native[tag] = audit
    return {
        "status": "validated", "nativeInputs": inputs,
        "childNative": child_native,
        "memberNames": list(child_native["selectedReadOrder"]),
        "parentNative": parent_native, "bindings": bindings,
    }


def decode_blackboard_double_action_child_receipt(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    tag: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Replay the exact parent action, then name its selected child span."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}:native-not-validated")
    if tag not in _PARENTS or tag not in native_validation.get("bindings", {}):
        raise ValueError(f"{LABEL}:unsupported-parent-tag={tag:#x}")
    binding = native_validation["bindings"][tag]
    _validator, decoder = _PARENTS[tag]
    parent = decoder(
        data, source=source, logical_sha256=logical_sha256,
        start=start, end=end, native_validation=native_validation["parentNative"][tag],
    )
    if (
        parent.get("schema") != binding["parentSchema"]
        or parent.get("status") != "named-wrapper-exact-span"
        or parent.get("tag") != tag
        or parent.get("wholeActionByteSpanExact") is not True
        or parent.get("start") != start or parent.get("end") != end
        or parent.get("source") != source
        or parent.get("logicalSha256") != logical_sha256.upper()
    ):
        raise ValueError(f"{LABEL}:parent-receipt-drift")
    fields = [field for field in parent["namedFields"]
              if field["fieldName"] == binding["fieldName"]
              and field["kind"] == binding["kind"]]
    if len(fields) != 1:
        raise ValueError(f"{LABEL}:parent-field-missing-or-ambiguous")
    field = fields[0]
    child_receipt = child.decode_adding_cooldown(
        data, field["start"], field["end"],
        native_validation=native_validation["childNative"],
    )
    if (child_receipt.get("wholeValueExact") is not True
            or child_receipt["startOffset"] != field["start"]
            or child_receipt["consumedEnd"] != field["end"]
            or (child_receipt["fields"] and [row["name"] for row in child_receipt["fields"]]
                != native_validation["memberNames"])):
        raise ValueError(f"{LABEL}:child-field-drift")
    return {
        "schema": SCHEMA, "status": "named-stored-child-exact-span",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "parentTag": tag, "parentActionRange": [start, end],
        "parentField": binding["fieldName"],
        "parentFieldRange": [field["start"], field["end"]],
        "providerType": DOUBLE_TYPE, "child": child_receipt,
        "wholeProviderByteSpanExact": True,
        "wholeActionRecursiveSchemaExact": False,
        "wholeBuffDataExact": False,
        "evidenceBoundary": (
            "Selected parent source and wrapper name this BlackboardDouble field; "
            "the separately selected child reader names its stored members at "
            "the exact source-hash-checked field extent. String decoding, live "
            "blackboard provider choice, evaluation and other action interiors "
            "remain unresolved."
        ),
    }
