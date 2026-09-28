"""Selected native direct SelectorData members inside Buff targets.

The parent TargetSettings adapter owns `selectorData` and its exact span.
This reader names the SelectorData union and two list fields through the
selected derived plan and source MethodSpec. Finder/validator bodies remain
structural, without a live target-selection claim.

The three direct stored members are, in order, ``finderData``,
``postProcessorData`` and ``validatorData``. The reader reparses its parent
target, records the finder union's selected tag/type and both list counts,
and must end at the parent's independently fixed selector boundary. Exact
subtype children are separate modules: ``buff_selector_finder_character_team``
(finder tag 2), ``buff_selector_finder_owner_spawned`` (finder tag 13),
``buff_selector_validator_zero`` (validator tags 5 and 9) and
``buff_selector_validator_tag_query`` (validator tag 11). Other positive
finder subtype bodies remain structural.
"""
from __future__ import annotations

import struct
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack import buff_modify_dynamic_blackboard_action_receipt as modify
from scripts.game_data.memorypack import buff_target_settings_child_receipt as target
from scripts.game_data.memorypack.derived_values import ValueReader


SCHEMA = "endfield.buff-selector-data-action-child-receipt.v1"
LABEL = "buffSelectorDataActionChild"
SELECTOR_TYPE = "Beyond.Gameplay.Core.Selector+SelectorData"
SELECTOR_WRAPPER = "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_SelectorDataForMemoryPack"
FIELD_NAME = "selectorData"


def _setter_name(row: list[Any] | tuple[Any, ...]) -> str:
    name = row[1]
    if not isinstance(name, str) or not name.startswith("set___") or not name.endswith("__"):
        raise ValueError(f"{LABEL}.native:setter-name")
    return name.removeprefix("set___").removesuffix("__")


def validate_current_native_contract(
    *, target_native: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check target ownership, Selector source MethodSpec and setter order."""
    if target_native is None:
        target_native = target.validate_current_native_contract()
    if target_native.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:target-not-validated")
    registry = target_native["_registry"]
    target_definition = target_native["targetDefinition"]
    parent_members = [row for row in registry.plans[target_definition]
                      if row.name == FIELD_NAME]
    if (len(parent_members) != 1 or parent_members[0].kind != "object"
            or parent_members[0].ref not in registry.plans
            or registry.wrapped_names.get(parent_members[0].ref) != SELECTOR_TYPE):
        raise ValueError(f"{LABEL}.native:target-selector-field")
    definition = parent_members[0].ref
    plan = registry.plans[definition]
    source, _catalog = modify._contracts()
    if len(plan) != len(source["anonymousReadOrder"]["member3"]):
        raise ValueError(f"{LABEL}.native:selector-member-count")
    union_members = [row for row in plan if row.kind == "union"
                     and row.ref in registry.union_tag_maps]
    if len(union_members) != 1 or not registry.union_tag_maps[union_members[0].ref]:
        raise ValueError(f"{LABEL}.native:finder-union-plan")
    if sum(row.kind == "list" for row in plan) != len(plan) - 1:
        raise ValueError(f"{LABEL}.native:selector-list-plan")
    expected = target_native["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != "validated":
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    image = open_native_image(gate.gameassembly, gate.metadata)
    methods = [row for row in source["methods"] if row[1] == SELECTOR_WRAPPER]
    if len(methods) != 1:
        raise ValueError(f"{LABEL}.native:selector-reader-count={len(methods)}")
    image.validate_method_row(methods[0], label=LABEL)
    image.check_windows(source["codeWindows"], label=LABEL)
    owners = [row for row in image.metadata.types
              if image.metadata.type_full_name(row) == SELECTOR_WRAPPER]
    if len(owners) != 1:
        raise ValueError(f"{LABEL}.native:selector-wrapper-count={len(owners)}")
    names = [_setter_name(row) for row in image.setter_methods(
        owners[0], parameter="typeName", label=LABEL
    )]
    if names != [member.name for member in plan]:
        raise ValueError(f"{LABEL}.native:selector-setter-order")
    contexts = [row for row in source["nestedContexts"]
                if row.get("typeName") == SELECTOR_TYPE]
    if len(contexts) != 1:
        raise ValueError(f"{LABEL}.native:selector-context-count={len(contexts)}")
    context = contexts[0]
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    spec_index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"],
        source=str(gate.gameassembly), offset=cell,
    )
    if spec_index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:selector-method-spec-index")
    raw = image.pe.bytes_at_va(
        int(image.registration["methodSpecs"], 16) + spec_index * 12, 12
    )
    if list(struct.unpack("<iii", raw)) != context["methodSpec"]:
        raise ValueError(f"{LABEL}.native:selector-method-spec")
    arguments = image.instantiations.resolve(context["methodSpec"][2]).arguments
    if (len(arguments) != 1
            or arguments[0].raw_type_record_hex.upper() != context["argumentRawHex"].upper()
            or image.type_name(context["typeDefinition"]) != context["typeName"]):
        raise ValueError(f"{LABEL}.native:selector-type")
    return {
        "status": "validated", "nativeInputs": expected,
        "targetNative": target_native,
        "selectorDefinition": definition,
        "directMemberNames": names,
        "finderUnionMember": union_members[0].name,
        "_registry": registry,
    }


def decode_selector_data_action_child_receipt(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    tag: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Reparse parent targets, then name each bounded selector child."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}:native-not-validated")
    parent = target.decode_target_settings_action_child_receipt(
        data, source=source, logical_sha256=logical_sha256,
        start=start, end=end, tag=tag,
        native_validation=native_validation["targetNative"],
    )
    if (parent.get("status") != "named-direct-target-members"
            or parent.get("wholeActionRecursiveSchemaExact") is not False
            or parent.get("wholeBuffDataExact") is not False):
        raise ValueError(f"{LABEL}:target-parent-drift")
    registry = native_validation["_registry"]
    definition = native_validation["selectorDefinition"]
    plan = registry.plans[definition]
    if [member.name for member in plan] != native_validation["directMemberNames"]:
        raise ValueError(f"{LABEL}:selector-plan-drift")
    selectors = []
    for target_child in parent["targetChildren"]:
        if target_child["status"] != "named-direct-members-exact-span":
            raise ValueError(f"{LABEL}:null-or-unsupported-parent-target")
        fields = [field for field in target_child["namedMembers"]
                  if field["fieldName"] == FIELD_NAME and field["kind"] == "object"]
        if len(fields) != 1:
            raise ValueError(f"{LABEL}:selector-field-missing-or-ambiguous")
        field = fields[0]
        reader = ValueReader(data, source, field["end"], registry=registry)
        reader.pos = field["start"]
        if reader.peek() == 0xFF:
            reader.take(1, "null-selector-data")
            members = []
            status = "exact-null"
        else:
            reader.header(len(plan))
            members = []
            for member in plan:
                member_start = reader.pos
                value = reader._value_member(member, 1)
                if reader.pos <= member_start:
                    raise ValueError(f"{LABEL}:selector-member-no-progress:{member.name}")
                row = {"fieldName": member.name, "kind": member.kind,
                       "start": member_start, "end": reader.pos,
                       "nestedBodyStructural": True}
                if member.kind == "union":
                    row["unionTag"] = None if value is None else value["$tag"]
                    row["selectedSubtype"] = None if value is None else value["$type"]
                elif member.kind == "list":
                    row["count"] = None if value is None else len(value)
                members.append(row)
            status = "named-direct-members-exact-span"
        if reader.pos != field["end"]:
            raise ValueError(f"{LABEL}:selector-end={reader.pos}; expected={field['end']}")
        selectors.append({
            "targetParentField": target_child["parentField"],
            "start": field["start"], "end": field["end"],
            "status": status, "namedMembers": members,
            "wholeStoredSpanExact": True,
            "recursiveNamedSchemaExact": False,
        })
    return {
        "schema": SCHEMA, "status": "named-direct-selector-members",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "parentTag": tag, "parentActionRange": [start, end],
        "selectorChildren": selectors,
        "wholeActionRecursiveSchemaExact": False,
        "wholeBuffDataExact": False,
        "evidenceBoundary": (
            "The selected TargetSettings reader owns each selectorData extent, "
            "and the selected SelectorData reader and generated setters name its "
            "finder union and two list fields. Reached finder tags are selected "
            "through the native-derived union map; nested finder, validator and "
            "postprocessor bodies remain structural. Runtime target selection "
            "and enclosing action/BuffData recursive schemas remain unresolved."
        ),
    }
