"""Which ActionBase members hold an EntityPtr, for the selected build.

Story binds a LevelScript action to the entities it names by reading the
action's ``Param<EntityPtr>`` members. The contract lists, for each authored
action, those members' names and serialized ordinals, the managed field
offsets, and the action's current union tag and member count. None of that is
reviewed by hand: ``--regenerate`` derives it from the installed build -- tags
from ``levelscript_union_tags``, members and their declared types from
``memorypack.wrapper_members``, offsets from the metadata registration.

What stays authored is which actions Story reads, the ``nonEntityContract``
flag for actions Story must skip, and ``serializedRecordLayouts``, which are
bound to specific data files by their own hashes rather than to the build.

Run as: python -m scripts.game_data.action_entity_fields_native --regenerate [--write]
"""
from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR

SCHEMA = "actionEntityFieldNativeContract.v3"
DEFAULT_CONTRACT = CONTRACTS_DIR / "action_entity_fields.json"
#: Stable identifier cited in Story evidence; the build lives in the contract.
NATIVE_MAPPING_ID = "action-entity-formatter-fields.v3"
ENTITY_PARAM_TYPE = "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.EntityPtr>"
ENTITY_PTR_TYPE = "Beyond.Gameplay.Core.EntityPtr"


@lru_cache(maxsize=1)
def load_action_entity_field_contract(
    contract_path: Path = DEFAULT_CONTRACT,
) -> tuple[dict[tuple[int, int], dict[str, Any]], dict[str, Any]]:
    """Rows keyed by current ``(unionTag, serializedMemberCount)``, or nothing."""
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"validator": "actionEntityFieldNativeContract", "gate": gate,
                         "expected": expected, "actual": actual})

    try:
        contract = json.loads(Path(contract_path).read_bytes().decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        reject("read_valid_json", True, str(error)[:400])
        return {}, {"status": "validation_failed", "nativeMappingId": NATIVE_MAPPING_ID,
                    "validationFailures": failures}
    for gate, expected, actual in (("schema", SCHEMA, contract.get("schema")),
                                   ("status", "validated", contract.get("status"))):
        if actual != expected:
            reject(gate, expected, actual)
    inputs = contract.get("nativeInputs") or {}
    native = check_installed_native_inputs(
        str(inputs.get("gameAssemblySha256") or ""), str(inputs.get("metadataSha256") or ""))
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject("installed_native_inputs", NATIVE_EVIDENCE_VALIDATED,
               {"status": native.status, "detail": native.detail})
    out: dict[tuple[int, int], dict[str, Any]] = {}
    for action in contract.get("actions") or []:
        key = (action.get("unionTag"), action.get("serializedMemberCount"))
        if not isinstance(action, dict) or not all(isinstance(value, int) for value in key) or key in out:
            reject("unique_action_key", "unique integer pair", key)
            continue
        fields = action.get("entityFields")
        if not isinstance(fields, list):
            reject("entity_fields", "list", type(fields).__name__)
            continue
        if bool(action.get("nonEntityContract")) != (not fields):
            reject("non_entity_contract", "true exactly when no EntityPtr member exists",
                   {"action": action.get("actionName"), "fields": len(fields)})
            continue
        ordinals = [field.get("constantPointerOrdinal") for field in fields]
        if ordinals != list(range(len(fields))):
            reject("constant_pointer_ordinals", list(range(len(fields))), ordinals)
            continue
        out[key] = action
    if failures:
        out = {}
    return out, {
        "status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed",
        "nativeMappingId": NATIVE_MAPPING_ID,
        "validationFailures": failures,
    }


def regenerate(contract: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Re-derive every per-build field for the authored action set."""
    from scripts.game_data import levelscript_union_tags as union_tags
    from scripts.game_data.il2cpp import protocol
    from scripts.game_data.il2cpp.native_image import NativeImage
    from scripts.game_data.memorypack.wrapper_members import derive_from_image

    native = check_installed_native_inputs()
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        raise SystemExit(f"installed native inputs: {native.status}: {native.detail}")
    if union_tags.union_tags_audit()["status"] != NATIVE_EVIDENCE_VALIDATED:
        raise SystemExit("levelscript_union_tags.json does not describe the installed build")
    image = NativeImage(native.gameassembly, native.metadata, label="actionEntityFields")
    wrappers = derive_from_image(image)
    by_wrapped = {wrapper.wrapped_type: wrapper for wrapper in wrappers.values() if wrapper.wrapped_type}
    by_wrapper = {wrapper.name: wrapper for wrapper in wrappers.values()}
    type_index = {image.metadata.type_full_name(t): i for i, t in enumerate(image.metadata.types)}
    entity_ptr = by_wrapped.get(ENTITY_PTR_TYPE)
    value_fields = [member.name for member in entity_ptr.members] if entity_ptr else []

    refused: list[str] = []
    actions = []
    for authored in contract.get("actions") or []:
        name = authored["actionName"]
        tag = union_tags.action(name)
        wrapper = by_wrapper.get(union_tags.wrapper_name("ActionBase", name))
        if not isinstance(tag[0], int) or wrapper is None:
            refused.append(f"{name}: not an ActionBase type in the current build")
            continue
        if tag[1] != len(wrapper.members):
            refused.append(f"{name}: union-tag member count {tag[1]} differs from wrapper {len(wrapper.members)}")
            continue
        index = type_index.get(wrapper.wrapped_type or "")
        try:
            offsets = protocol.runtime_type_field_offsets(
                image.metadata, image.pe, image.registration, index) if index is not None else {}
        except RuntimeError:
            # A type with no runtime offset row still serializes the same
            # members; only the managed offset is then unrecorded.
            offsets = {}
        entity_members = [(ordinal, member) for ordinal, member in enumerate(wrapper.members)
                          if member.declared_type == ENTITY_PARAM_TYPE]
        row = {
            "actionName": name,
            "unionTag": tag[0],
            "serializedMemberCount": tag[1],
            "entityFields": [
                {"fieldName": member.name, "memberOrdinalZeroBased": ordinal,
                 "constantPointerOrdinal": position,
                 "fieldOffset": hex(offsets[member.name]) if member.name in offsets else None}
                for position, (ordinal, member) in enumerate(entity_members)
            ],
        }
        if not entity_members:
            row["nonEntityContract"] = True
        else:
            row["serializedValueLayout"] = {
                "managedType": "Beyond.Gameplay.Actions.Param<Beyond.Gameplay.Core.EntityPtr>",
                "valueFields": value_fields,
            }
        if bool(authored.get("nonEntityContract")) != bool(row.get("nonEntityContract")):
            refused.append(f"{name}: nonEntityContract changed; review which members it reads")
        if authored.get("serializedRecordLayouts"):
            row["serializedRecordLayouts"] = authored["serializedRecordLayouts"]
            known = {field["fieldName"] for field in row["entityFields"]}
            for layout in authored["serializedRecordLayouts"]:
                for state in layout.get("fieldStates") or []:
                    if state.get("fieldName") not in known:
                        refused.append(f"{name}: recorded layout names {state.get('fieldName')}, "
                                       "which is no longer an EntityPtr member")
        actions.append(row)
    return {
        "schema": SCHEMA,
        "status": "validated",
        "evidenceBoundary": {
            "exact": "union tag from the ActionBase formatter switch; members, declared types and order from generated wrapper setters; field offsets from the metadata registration",
            "unresolved": "what each action does with the entity at runtime",
        },
        "nativeInputs": {"gameAssemblySha256": native.gameassembly_sha256.upper(),
                         "metadataSha256": native.metadata_sha256.upper()},
        "actionCount": len(actions),
        "actions": sorted(actions, key=lambda row: row["unionTag"]),
    }, refused


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if not args.regenerate:
        _rows, audit = load_action_entity_field_contract(args.contract)
        print(json.dumps(audit, indent=1))
        return 0 if audit["status"] == NATIVE_EVIDENCE_VALIDATED else 1
    regenerated, refused = regenerate(json.loads(args.contract.read_bytes().decode("utf-8-sig")))
    print(json.dumps({"refused": refused, "actions": regenerated["actionCount"]}, indent=1))
    if refused:
        return 1
    if args.write:
        args.contract.write_bytes((json.dumps(regenerated, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["load_action_entity_field_contract", "regenerate", "NATIVE_MAPPING_ID"]
