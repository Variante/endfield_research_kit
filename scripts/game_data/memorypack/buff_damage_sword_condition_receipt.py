"""Selected sword condition composition; diagnostic only, never Buff admission.

Existing child owners reparse every action and reached nested value. The
stored six-action tiling receipt remains unchanged; this composition adds
independent recursive child receipts and the authenticated sequence envelopes.
It requires the ModifyDynamicBlackboard parent's direct typed-call validation.
No runtime comparison, branch decision, damage effect or whole root is proved.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run from the repository root: python -m scripts.game_data.memorypack.buff_damage_sword_condition_receipt")

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.corpus_gate import _guard_output_path
from scripts.game_data.memorypack import buff_compare_float_blackboard_children as compare
from scripts.game_data.memorypack import buff_damage_check_entity_num_target_children as entity
from scripts.game_data.memorypack import buff_damage_modify_dynamic_blackboard_child_receipt as modify
from scripts.game_data.memorypack import buff_damage_sequence_action_condition_receipt as sequence
from scripts.game_data.memorypack import buff_damage_sword_condition_storage as storage
from scripts.game_data.memorypack import buff_if_else_action_receipt as envelope
from scripts.game_data.memorypack import buff_modify_dynamic_blackboard_action_receipt as modify_parent
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.buff-damage-sword-condition-receipt.v1"
LABEL = "buffDamageSwordConditionReceipt"


def _guard_cli_output(output: Path, inputs: list[Path], *, repo_root: Path = REPO_ROOT) -> Path:
    """Keep this generated diagnostic separate from every selected/source input."""
    root = repo_root.resolve()
    resolved = output.resolve()
    protected = [*inputs, root / "scripts", CONTRACTS_DIR, Path(__file__)]
    # A hard link under a generated root can still alias a reviewed source.
    # Directory containment alone does not detect that case.
    script_root = root / "scripts"
    if resolved.exists() and script_root.is_dir():
        protected.extend(path for path in script_root.rglob("*")
                         if path.is_file() and path.suffix in (".py", ".json", ".ps1", ".bat", ".cs", ".md"))
    protected.extend(root / name for name in ("serve.py", "export.bat", "endfield_paths.bat"))
    _guard_output_path(resolved, protected)
    if (not resolved.is_relative_to(root)
            or not any(resolved.is_relative_to(root / name) and resolved != root / name
                       for name in ("reports", "tmp", "scratch"))
            or resolved.is_dir()):
        raise ValueError(f"{LABEL}.output:outside-generated-roots expected=reports/tmp/scratch file actual={resolved}")
    return resolved


def _declarations() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = storage._contract()
    nested = storage.if_else._contract()
    serial = sequence._contract()
    selected = root["selectedSource"]
    if (nested["nativeInputs"] != root["nativeInputs"]
            or serial["nativeInputs"] != root["nativeInputs"]
            or any(nested["selectedSource"][key] != selected[key] for key in ("path", "sha256"))
            or serial["memberCount"] != selected["sequenceMemberCount"]
            or serial["terminalByteCount"] != selected["terminalByteCount"]):
        raise ValueError(f"{LABEL}.contract:existing-dependency-drift")
    return root, nested, serial


def _typed_modify_children(native: dict[str, Any]) -> None:
    source, _catalog = modify_parent._contracts()
    contract = modify._contract()
    expected = [
        {"fieldName": contract["selectedFieldNames"][index],
         "typeName": context["typeName"], "methodSpecIndex": context["methodSpecIndex"],
         "instructionRva": context["instructionRva"]}
        for index, context in zip((contract["targetFieldIndex"], contract["blackboardFieldIndex"]),
                                  source["nestedContexts"][:2], strict=True)
    ]
    if native.get("status") != "validated" or native.get("directTypedChildren") != expected:
        raise ValueError(
            f"{LABEL}.native:modify-direct-typed-children expected={expected} "
            f"actual={native.get('directTypedChildren')}"
        )


def validate_current_native_contract(audit_report_path: Path, *,
                                    gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Gate explicit selected inputs, then compose independent native owners."""
    root, _nested, serial = _declarations()
    expected = root["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"],
                                         gameassembly=gameassembly, metadata=metadata)
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "failedChild": "selectedNativeInputs"}
    parent = modify_parent.validate_current_native_contract(
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    _typed_modify_children(parent)
    owners = {}
    paths = {"gameassembly": gate.gameassembly, "metadata": gate.metadata}
    validators = (
        ("storage", lambda: storage.validate_current_native_contract(audit_report_path, **paths)),
        ("entity", lambda: entity.validate_current_native_contract(audit_report_path,
                         target_parent_tags=(modify_parent.TAG,), **paths)),
        ("compare", lambda: compare.validate_current_native_contract(**paths)),
        ("modify", lambda: modify.validate_current_native_contract(
                         target_parent_tags=(modify_parent.TAG,), **paths)),
        ("sequence", lambda: sequence.validate_current_native_contract(**paths)),
    )
    for name, validator in validators:
        native = validator()
        if native.get("status") != "validated":
            return {"status": native.get("status", "failed"), "failedChild": name,
                    "detail": str(native.get("detail", "independent native gate failed"))[:500]}
        owners[name] = native
    if (any(owners[name].get("nativeInputs") != expected for name in ("storage", "entity", "modify"))
            or owners["compare"].get("nativeInputs") != {name: expected[name] for name in ("GameAssembly.dll", "global-metadata.dat")}
            or owners["sequence"].get("serializedReadOrder") != serial["serializedReadOrder"]):
        raise ValueError(f"{LABEL}.native:child-build-or-sequence-drift")
    _typed_modify_children(owners["modify"]["actionNative"])
    return {"status": "validated", "nativeInputs": expected, "source": root["selectedSource"],
            "selectedNativePaths": {"GameAssembly.dll": str(gate.gameassembly), "global-metadata.dat": str(gate.metadata)},
            "directModifyNative": parent, **owners}


def _owned_span(receipt: dict[str, Any], span: dict[str, Any], *, source: str, digest: str) -> None:
    tag = receipt.get("tag", receipt.get("unionTag"))
    if (tag != span["tag"] or receipt.get("start") != span["start"] or receipt.get("end") != span["end"]
            or receipt.get("source") != source or receipt.get("logicalSha256") != digest
            or not (receipt.get("wholeStoredSpanExact") is True
                    or receipt.get("wholeActionByteSpanExact") is True
                    or receipt.get("wholeActionExact") is True)):
        raise ValueError(f"{LABEL}.action:owned-span expected={span} actualTag={tag} actualRange={[receipt.get('start'), receipt.get('end')]} source={source}")


def _sequence_receipt(data: bytes, *, source: str, start: int, end: int,
                      children: list[dict[str, Any]], serial: dict[str, Any]) -> dict[str, Any]:
    """Reuse the existing exact envelope reader with independently closed children."""
    if any(row.get("recursiveNamedSchemaExact") is not True for row in children):
        raise ValueError(f"{LABEL}.sequence:unproved-child source={source} range={[start, end]}")
    spans = {row["start"]: {"tag": row["tag"], "end": row["end"]} for row in children}
    if len(spans) != len(children):
        raise ValueError(f"{LABEL}.sequence:duplicate-child")
    reader = Reader(data, source, end)
    reader.pos = start
    envelope._read_sequence(reader, spans)
    if reader.pos != end:
        raise ValueError(f"{LABEL}.sequence:end expected={end} actual={reader.pos} source={source}")
    names = serial["serializedReadOrder"][1:]
    terminal_start = end - serial["terminalByteCount"]
    if len(names) != serial["terminalByteCount"]:
        raise ValueError(f"{LABEL}.sequence:terminal-declaration-drift")
    return {"start": start, "end": end, "actionCount": len(children), "actions": children,
            "terminal": [{"name": name, "start": terminal_start + index, "end": terminal_start + index + 1,
                          "rawByte": data[terminal_start + index]}
                         for index, name in enumerate(names)],
            "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True}


def decode_selected_condition(data: bytes, *, source: str,
                              native_validation: dict[str, Any]) -> dict[str, Any]:
    root, nested_contract, serial = _declarations()
    selected = root["selectedSource"]
    native = native_validation
    if (native.get("status") != "validated" or native.get("nativeInputs") != root["nativeInputs"]
            or native.get("source") != selected
            or any(native.get(name, {}).get("status") != "validated" for name in ("storage", "entity", "compare", "modify", "sequence"))
            or any(native.get(name, {}).get("nativeInputs") != root["nativeInputs"] for name in ("storage", "entity", "modify"))
            or native.get("compare", {}).get("nativeInputs") != {name: root["nativeInputs"][name] for name in ("GameAssembly.dll", "global-metadata.dat")}
            or native.get("sequence", {}).get("serializedReadOrder") != serial["serializedReadOrder"]):
        raise ValueError(f"{LABEL}.native:unvalidated actual={native.get('status')} source={source}")
    _typed_modify_children(native.get("directModifyNative", {}))
    _typed_modify_children(native["modify"].get("actionNative", {}))
    digest = hashlib.sha256(data).hexdigest().upper()
    if source != selected["path"] or digest != selected["sha256"]:
        raise ValueError(f"{LABEL}.source:path-or-sha256 expected={selected['path']}:{selected['sha256']} actual={source}:{digest}")
    stored = storage.decode_selected_condition(data, source=source, native_validation=native["storage"])
    spans = selected["actionSpans"]
    actions = stored.get("actions", [])
    if len(actions) != len(spans) or stored.get("wholeStoredSpanExact") is not True:
        raise ValueError(f"{LABEL}.storage:incomplete")
    for action, span in zip(actions, spans, strict=True):
        # The prefix's first two receipts inherit source authentication from its
        # enclosing receipt rather than restating its path/hash on each action.
        _owned_span({"source": source, "logicalSha256": digest, **action}, span, source=source, digest=digest)
    if actions[0].get("recursiveNamedSchemaExact") is not True or actions[1].get("wholeActionExact") is not True:
        raise ValueError(f"{LABEL}.prefix:unproved-actions")
    composed = [{**action, "recursiveNamedSchemaExact": True} for action in actions[:2]]
    target = entity.decode_selected_target_children(data, source=source, native_validation=native["entity"])
    parent = actions[2]
    fields = [row for row in parent["namedFields"] if row["kind"] in ("object", "union", "list", "map", "profile")]
    if (target.get("wholeTargetStoredSchemaExact") is not True or target.get("parentActionRange") != [parent["start"], parent["end"]]
            or target.get("source") != source or target.get("logicalSha256") != digest
            or len(fields) != 1 or fields[0]["name"] != target.get("targetField")
            or [fields[0]["start"], fields[0]["end"]] != [target.get("start"), target.get("end")]):
        raise ValueError(f"{LABEL}.entity:parent-target-join source={source}")
    composed.append({**parent, "namedTargetChild": target, "recursiveNamedSchemaExact": True})
    nested_specs = nested_contract["selectedSource"]["nestedActions"]
    compare_spec = next(row for row in nested_specs if row["tag"] == compare.parent.TAG)
    operands = compare.decode_compare_float_blackboard_children(
        data, source=source, logical_sha256=digest, start=compare_spec["start"], end=compare_spec["end"], native_validation=native["compare"])
    comparison = operands["parent"]
    _owned_span(comparison, compare_spec, source=source, digest=digest)
    if (operands.get("wholeOperandByteSpansExact") is not True
            or set(comparison.get("nestedStructuralFields", [])) != {row["parentField"] for row in operands["children"]}):
        raise ValueError(f"{LABEL}.compare:unproved-operand")
    comparison = {**comparison, "namedOperandChildren": operands["children"], "recursiveNamedSchemaExact": True}
    modify_specs = [row for row in nested_specs if row["tag"] == modify_parent.TAG] + spans[4:]
    modifications = []
    for span in modify_specs:
        receipt = modify.decode_modify_dynamic_blackboard_child(
            data, source=source, logical_sha256=digest, start=span["start"], end=span["end"], native_validation=native["modify"])
        _owned_span(receipt, span, source=source, digest=digest)
        if receipt.get("recursiveNamedSchemaExact") is not True:
            raise ValueError(f"{LABEL}.modify:unproved-child source={source} range={[span['start'], span['end']]}")
        modifications.append({**receipt, "tag": span["tag"]})
    if_else = actions[3]
    sequence_fields = [row for row in if_else["namedFields"] if row["kind"] == "SequenceActionData"]
    expected_roles = {row["role"] for row in nested_specs} | {"failActions"}
    if {row["fieldName"] for row in sequence_fields} != expected_roles or len(sequence_fields) != len(expected_roles):
        raise ValueError(f"{LABEL}.ifElse:sequence-member-join")
    role_children = {compare_spec["role"]: [comparison], modify_specs[0]["role"]: [modifications[0]], "failActions": []}
    branches = [{"parentField": field["fieldName"], "receipt": _sequence_receipt(
        data, source=source, start=field["start"], end=field["end"], children=role_children[field["fieldName"]], serial=serial)}
        for field in sequence_fields]
    composed.append({**if_else, "namedSequenceChildren": branches, "recursiveNamedSchemaExact": True})
    composed.extend(modifications[1:])
    condition = _sequence_receipt(data, source=source, start=selected["conditionStart"],
                                  end=selected["conditionEnd"], children=composed, serial=serial)
    return {"schema": SCHEMA, "status": "recursive-selected-condition-stored-schema",
            "selectedOnly": True, "publicationEligible": False, "source": source, "logicalSha256": digest,
            **condition, "topLevelActionCount": len(composed), "nestedActionCount": len(nested_specs),
            "wholeConditionStoredSchemaExact": True, "wholeConditionExact": False, "wholeBuffDataExact": False,
            "evidenceBoundary": "Independent native-gated action and child owners close every reached stored member and sequence envelope on this selected source. Runtime values, branch results, effects, and whole BuffData admission remain unproved."}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--audit-report", required=True, type=Path)
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    protected = [args.source_file, args.gameassembly, args.metadata, args.audit_report,
                 args.gameassembly.parent / "UnityPlayer.dll"]
    try:
        output = _guard_cli_output(args.output, protected)
    except ValueError as exc:
        parser.error(str(exc))
    native = validate_current_native_contract(args.audit_report, gameassembly=args.gameassembly, metadata=args.metadata)
    if native.get("status") != "validated":
        print(json.dumps({"status": native.get("status"), "failedChild": native.get("failedChild"), "detail": native.get("detail")}))
        return 1
    receipt = decode_selected_condition(args.source_file.read_bytes(), source=native["source"]["path"], native_validation=native)
    output = _guard_cli_output(output, protected)
    atomic_write_text(output, json.dumps({"schema": SCHEMA, "status": "validated-selected-condition", "publicationEligible": False,
                                        "nativeInputs": native["nativeInputs"], "selectedNativePaths": native["selectedNativePaths"], "receipt": receipt}, indent=2) + "\n")
    print(json.dumps({"status": "validated-selected-condition", "topLevelActions": receipt["topLevelActionCount"], "nestedActions": receipt["nestedActionCount"], "wholeBuffDataExact": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
