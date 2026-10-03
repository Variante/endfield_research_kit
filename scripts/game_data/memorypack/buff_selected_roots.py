"""Complete-family admission of four independently proved Buff root sources.

Selected child/root APIs remain unpublished diagnostics. Only the full Buff
corpus may attach a receipt after the current ledger has authenticated logical
bytes. The registry independently repeats these same reads and compares the
canonical receipt. No anonymous nested storage, live behavior or provider
selection is promoted here.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from scripts.common import REPORTS_DIR, canonical_json_sha256, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import buff_root_no_positive as root
from scripts.game_data.memorypack import buff_heal_processor_zero as heal
from scripts.game_data.memorypack import buff_break_passing_selected as passing
from scripts.game_data.memorypack import buff_empty_condition_tag_ten_selected as empty_ten
from scripts.game_data.memorypack import buff_damage_sword_selected as sword
from scripts.game_data.memorypack import corpus_gate as gate
from scripts.game_data.memorypack.action_dispatcher import reviewed_switch_table

DEFAULT_NATIVE_AUDIT = REPORTS_DIR / "animestudio/il2cpp_context_current_latest.json"
ROUTES = {
    "positiveHeal": (heal, root.decode_selected_positive_heal_buff,
                     "positive_heal_validation", "endfield.buff-root-selected-positive-heal-receipt.v1"),
    "breakPassing": (passing, root.decode_selected_break_passing_buff,
                     "break_passing_validation", "endfield.buff-root-selected-break-passing-receipt.v1"),
    "emptyConditionTagTen": (empty_ten, root.decode_selected_empty_condition_tag_ten_buff,
                           "empty_tag_ten_validation", "endfield.buff-root-selected-empty-condition-tag-ten-receipt.v2"),
    "swordDamage": (sword, root.decode_selected_sword_damage_buff,
                   "sword_validation", "endfield.buff-root-selected-sword-damage-receipt.v1"),
}
ROOT_CHILDREN = ("addingCooldown", "dispelConfig", "iconConfig", "stackingSettings",
                 "timelineActions", "blackboardDataPairs", "globalModifier")
OLD_RECEIPTS = ("rootNoPositiveReceipt", "rootPositiveDamageReceipt", "rootSingleCreateActionReceipt")


def _contracts() -> dict[str, dict[str, Any]]:
    contracts = {name: module._contract() for name, (module, *_rest) in ROUTES.items()}
    paths = [value["selectedSource"]["path"] for value in contracts.values()]
    if len(set(paths)) != len(paths):
        gate._fail("buff-selected-root-overlapping-selection", source="selected root contracts",
                   expected="one distinct logical path per cohort", actual=paths)
    return contracts


def _contract_reference_names(value: Any):
    """Reviewed declarations use basename references, never generated paths."""
    if isinstance(value, dict):
        for child in value.values():
            yield from _contract_reference_names(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _contract_reference_names(child)
    elif isinstance(value, str) and Path(value).name == value and value.endswith(".json"):
        yield value


def _contract_source_paths(parser_paths: list[Path]) -> set[Path]:
    # Re-enumerate every time: a newly relevant or conflicting dispatcher
    # declaration must change/fail the path set, even if an old unrelated file
    # now supplies it. Only contributing declarations become byte pins.
    table, _routes = reviewed_switch_table(CONTRACTS_DIR)
    pending = [CONTRACTS_DIR / name for name in (*table.contracts, "levelscript_union_tags.json")]
    for path in parser_paths:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                pending.extend(CONTRACTS_DIR / name for name in _contract_reference_names(node.value)
                               if (CONTRACTS_DIR / name).is_file())
    seen = set()
    while pending:
        path = pending.pop().resolve()
        if path in seen:
            continue
        seen.add(path)
        try:
            declaration = json.loads(path.read_bytes())
        except (OSError, ValueError) as exc:
            gate._fail("buff-selected-root-dependency-readable", source=path.as_posix(),
                       expected="reviewed contract JSON", actual=str(exc)[:240])
        pending.extend(CONTRACTS_DIR / name for name in _contract_reference_names(declaration)
                       if (CONTRACTS_DIR / name).is_file())
    return seen


def _source_paths(audit_path: Path, native_paths: list[Path]) -> list[Path]:
    parser_paths = gate._package_import_closure(Path(__file__))
    paths = set(parser_paths)
    paths.update(_contract_source_paths(parser_paths))
    paths.update(native_paths)
    paths.add(audit_path)
    return sorted({path.resolve() for path in paths}, key=lambda path: path.as_posix())


def assert_source_path_set(*, sources: list[Mapping[str, Any]], audit_path: Path,
                           native_paths: list[Path]) -> None:
    """Re-enumerate dynamic dependencies after an owner has checked byte pins.

    This deliberately does not hash native binaries again. Callers still own
    source fingerprint authentication; newly relevant/conflicting dispatcher
    declarations cannot hide outside that already-checked set.
    """
    current_paths = [path.as_posix() for path in _source_paths(audit_path, native_paths)]
    recorded_paths = [row["path"] for row in sources]
    if current_paths != recorded_paths:
        gate._fail("buff-selected-root-input-set-drift", source="selected root source inputs",
                   expected={"files": len(recorded_paths), "removed": sorted(set(recorded_paths) - set(current_paths))[:8]},
                   actual={"files": len(current_paths), "added": sorted(set(current_paths) - set(recorded_paths))[:8]})


def recheck_sources(context: Mapping[str, Any]) -> list[dict[str, Any]]:
    assert_source_path_set(sources=context["sources"], audit_path=Path(context["audit"]["path"]),
                           native_paths=context["nativePaths"])
    return gate._snapshot_pinned_files(context["sources"], label="Buff selected root inputs")


def prepare_native_context(*, audit_path: Path = DEFAULT_NATIVE_AUDIT,
                           root_validation: Mapping[str, Any]) -> dict[str, Any]:
    """Pin inputs before running current root/child validators; never run an audit."""
    contracts = _contracts()
    expected_inputs = root._native_contract()["nativeInputs"]
    if (root_validation.get("status") != "validated"
            or root_validation.get("nativeInputs") != expected_inputs
            or any((root_validation.get("children") or {}).get(name, {}).get("status") != "validated"
                   for name in ROOT_CHILDREN)):
        gate._fail("buff-selected-root-native-root", source="Buff root native validation",
                   expected="current root and every reached child validated", actual=root_validation.get("status"))
    native = check_installed_native_inputs(expected_inputs["GameAssembly.dll"],
                                           expected_inputs["global-metadata.dat"])
    if native.status != "validated":
        gate._fail("buff-selected-root-native-inputs", source="installed native inputs",
                   expected="validated", actual={"status": native.status, "detail": native.detail})
    native_paths = [Path(native.gameassembly), Path(native.metadata),
                    Path(native.gameassembly).parent / "UnityPlayer.dll"]
    for path in native_paths:
        pin = gate._fingerprint(path)
        if pin["sha256"] != expected_inputs[path.name]:
            gate._fail("buff-selected-root-native-hash", source=pin["path"],
                       expected=expected_inputs[path.name], actual=pin["sha256"])
    audit_pin = gate._fingerprint(audit_path)
    sources = [gate._fingerprint(path) for path in _source_paths(audit_path, native_paths)]
    try:
        audit = json.loads(audit_path.read_bytes())
    except (OSError, ValueError) as exc:
        gate._fail("buff-selected-root-audit-readable", source=str(audit_path),
                   expected="current selected Buff native audit", actual=str(exc)[:240])
    validations: dict[str, Any] = {}
    for name, (module, *_rest) in ROUTES.items():
        try:
            if name == "positiveHeal":
                validation = module.validate_current_native_contract(audit)
            elif name == "swordDamage":
                validation = module.validate_current_native_contract(audit_path,
                    gameassembly=native.gameassembly, metadata=native.metadata)
            else:
                validation = module.validate_current_native_contract()
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            gate._fail("buff-selected-root-native-validation", source=str(module.CONTRACT_PATH),
                       expected="current selected root child proof", actual=f"{type(exc).__name__}: {exc}"[:400])
        if (validation.get("status") != "validated"
                or validation.get("nativeInputs") != expected_inputs
                or validation.get("selectedSource") != contracts[name]["selectedSource"]):
            gate._fail("buff-selected-root-native-validation", source=str(module.CONTRACT_PATH),
                       expected="validated selected child with the same root native inputs",
                       actual={"status": validation.get("status"), "detail": validation.get("detail")})
        validations[name] = validation
        _selected_native(name, contracts[name]["selectedSource"], root_validation, validation)
        if name == "swordDamage":
            _sword_selected_paths(validation, audit_pin=audit_pin, native_paths=native_paths)
    context = {"audit": audit_pin, "sources": sources, "nativePaths": native_paths,
               "validations": validations, "contracts": contracts}
    recheck_sources(context)
    return context


def verify_saved_provenance(provenance: Mapping[str, Any]) -> dict[str, Any]:
    """Authenticate stored helper/contracts/audit/native pins before admission."""
    sources = provenance.get("buffSelectedRootSources")
    audit = provenance.get("buffSelectedRootNativeAudit")
    validations = provenance.get("buffSelectedRootNativeValidation")
    if (not isinstance(sources, list) or not all(isinstance(row, Mapping) for row in sources)
            or not isinstance(audit, Mapping) or not isinstance(validations, Mapping)
            or set(validations) != set(ROUTES)):
        gate._fail("buff-selected-root-provenance-missing", source="Buff report provenance",
                   expected="selected root source pins, native audit and all four native validations")
    checked = gate._snapshot_pinned_files(sources, label="Buff selected root inputs")
    checked_audit = gate._snapshot_pinned_files([audit], label="Buff selected root native audit")[0]
    if not any(pin["path"] == checked_audit["path"] and pin["sha256"] == checked_audit["sha256"]
               for pin in checked):
        gate._fail("buff-selected-root-audit-unpinned", source=checked_audit["path"],
                   expected="native audit included in selected source input pins")
    # An omitted parser/contract cannot turn into current evidence just because
    # the remaining saved files still match. The native binary paths must also
    # identify one opened build, with all three expected input files included.
    names = ("GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll")
    native_paths = [Path(pin["path"]) for pin in checked if Path(pin["path"]).name in names]
    if sorted(path.name for path in native_paths) != sorted(names):
        gate._fail("buff-selected-root-native-pins-missing", source="Buff selected root sources",
                   expected=list(names), actual=[path.name for path in native_paths])
    context = {"audit": dict(audit), "sources": checked, "nativePaths": native_paths}
    recheck_sources(context)
    for route, contract in _contracts().items():
        _selected_native(route, contract["selectedSource"],
                         provenance.get("buffRootNoPositiveNativeValidation") or {}, validations[route])
        if route == "swordDamage":
            _sword_selected_paths(validations[route], audit_pin=checked_audit, native_paths=native_paths)
    return {"sources": checked, "audit": dict(audit), "validations": validations}


def _selected_native(route: str, selected: Mapping[str, Any], root_validation: Mapping[str, Any],
                     validation: Mapping[str, Any]) -> None:
    expected_inputs = _contracts()[route]["nativeInputs"]
    if (root_validation.get("status") != "validated"
            or root_validation.get("nativeInputs") != expected_inputs
            or (root_validation.get("root") or {}).get("status") != "validated"
            or any((root_validation.get("children") or {}).get(name, {}).get("status") != "validated"
                   for name in ROOT_CHILDREN)
            or validation.get("status") != "validated"
            or validation.get("nativeInputs") != expected_inputs
            or validation.get("selectedSource") != selected):
        gate._fail("buff-selected-root-native-receipt", source=selected["path"],
                   expected="current root and selected child native proofs", actual=route)
    child_keys = {"positiveHeal": ("conditionNative", "blackboardNative"),
                  "breakPassing": ("root",),
                  "emptyConditionTagTen": ("root", "attribute", "modifier", "condition", "processorTen"),
                  "swordDamage": ("root", "modifier", "condition", "processor")}[route]
    if any((validation.get(key) or {}).get("status") != "validated" for key in child_keys):
        gate._fail("buff-selected-root-native-child", source=selected["path"],
                   expected={key: "validated" for key in child_keys}, actual=route)
    if route == "swordDamage":
        _sword_parent_typed_proof(validation, contract=_contracts()[route])


def _sword_parent_typed_proof(validation: Mapping[str, Any], *, contract: Mapping[str, Any]) -> None:
    expected = sword._parent_joins(contract)
    sites = {row[2]: row[0] for row in sword.modifier._contract()["childSourceInstructions"]}
    typed = validation.get("parentTypedChildren") or []
    source = contract["selectedSource"]["path"]
    if (not isinstance(typed, list) or len(typed) != len(expected)
            or any(not isinstance(row, Mapping) for row in typed)
            or any(row.get("fieldName") != join["fieldName"]
                   or row.get("methodSpecIndex") != join["methodSpecIndex"]
                   or row.get("instructionRva") != sites[join["sourceRole"]]
                   or row.get("typeName") != join["typeName"]
                   or row.get("setterType") != join["typeName"]
                   or row.get("destinationFieldType") != join["typeName"]
                   for row, join in zip(typed, expected))
            or any((validation.get(key) or {}).get("nativeInputs") != contract["nativeInputs"]
                   for key in ("root", "condition", "processor"))):
        gate._fail("buff-selected-root-sword-typed-parent", source=source,
                   expected="three exact selected parent argument/setter/destination type joins on the same native build",
                   actual=typed[:3] if isinstance(typed, list) else type(typed).__name__)


def _sword_selected_paths(validation: Mapping[str, Any], *, audit_pin: Mapping[str, Any],
                          native_paths: list[Path]) -> None:
    selected = validation.get("selectedNativePaths") or {}
    expected = {path.name: path.resolve().as_posix() for path in native_paths
                if path.name in ("GameAssembly.dll", "global-metadata.dat")}
    actual = {name: Path(path).resolve().as_posix() for name, path in selected.items()
              if isinstance(name, str) and isinstance(path, str)} if isinstance(selected, Mapping) else {}
    audit = validation.get("nativeAuditPath")
    if (actual != expected or not isinstance(audit, str)
            or Path(audit).resolve().as_posix() != audit_pin["path"]):
        gate._fail("buff-selected-root-sword-selected-inputs", source="sword selected native certificate",
                   expected={"nativePaths": expected, "auditPath": audit_pin["path"]},
                   actual={"nativePaths": actual, "auditPath": audit})


def _sword_receipt_complete(field: Mapping[str, Any], *, contract: Mapping[str, Any],
                            source: str, logical_sha256: str) -> bool:
    selected = contract["selectedSource"]
    selected_condition = sword.condition.storage._contract()["selectedSource"]
    condition_span = [selected_condition["conditionStart"], selected_condition["conditionEnd"]]
    plan = sword.processor._contract()
    child = field.get("child") or {}
    damage = child.get("damageModifier") or {}
    condition = damage.get("conditionChild") or {}
    processor = damage.get("processorChild") or {}
    enable = damage.get("enableSide") or {}
    parent = damage.get("parent") or {}
    elements = parent.get("elements") or []
    element = elements[0] if len(elements) == 1 else {}
    members = element.get("fields") or []
    top_actions = condition.get("actions") or []
    processors = members[1].get("processors") or [] if len(members) == 3 else []
    named = processor.get("namedFields") or []
    raw_side = enable.get("rawBitsHex")
    side_valid = (isinstance(raw_side, str) and len(raw_side) == 8
                  and all(char in "0123456789ABCDEF" for char in raw_side)
                  and type(enable.get("storedInt32")) is int
                  and int.from_bytes(bytes.fromhex(raw_side), "little", signed=True) == enable["storedInt32"])
    return (
        [field.get("start"), field.get("end")] == selected["damageModifier"] and field.get("count") == 1
        and child.get("schema") == sword.SCHEMA and child.get("status") == "exact-selected-sword-damage-child"
        and child.get("source") == source and child.get("logicalSha256") == logical_sha256
        and child.get("selectedOnly") is True and child.get("publicationEligible") is False
        and child.get("wholeBuffDataExact") is False and child.get("runtimeBehaviorObserved") is False
        and damage.get("status") == "exact-selected-sword-damage-list" and damage.get("count") == 1
        and [damage.get("startOffset"), damage.get("consumedEnd")] == selected["damageModifier"]
        and damage.get("wholeNamedSchemaExact") is True and damage.get("wholeListExact") is True
        and damage.get("recursiveNamedSchemaExact") is True
        and parent.get("status") == "named-direct-child-spans" and parent.get("count") == 1
        and [parent.get("startOffset"), parent.get("consumedEnd")] == selected["damageModifier"]
        and [element.get("start"), element.get("end")] == selected["item"]
        and [row.get("name") for row in members] == sword.modifier._contract()["selectedReadOrder"]
        and [[row.get("start"), row.get("end")] for row in members]
            == [condition_span, selected["processors"], selected["enableSide"]]
        and condition.get("schema") == sword.condition.SCHEMA
        and condition.get("status") == "recursive-selected-condition-stored-schema"
        and condition.get("source") == source and condition.get("logicalSha256") == logical_sha256
        and [condition.get("start"), condition.get("end")] == condition_span
        and condition.get("wholeConditionStoredSchemaExact") is True
        and condition.get("recursiveNamedSchemaExact") is True and condition.get("wholeStoredSpanExact") is True
        and condition.get("wholeConditionExact") is False and condition.get("wholeBuffDataExact") is False
        and condition.get("topLevelActionCount") == selected_condition["actionCount"]
        and len(top_actions) == selected_condition["actionCount"]
        and all(action.get("recursiveNamedSchemaExact") is True
                and {key: action.get(key) for key in ("tag", "start", "end")} == span
                for action, span in zip(top_actions, selected_condition["actionSpans"]))
        and members[0].get("actionUnionCount") == condition["topLevelActionCount"] + condition.get("nestedActionCount", -1)
        and members[1].get("count") == 1 and len(processors) == 1
        and [processors[0].get("start"), processors[0].get("end")] == selected["processor"]
        and processors[0].get("tag") == plan["unionTag"]
        and canonical_json_sha256(processors[0].get("namedChild")) == canonical_json_sha256(processor)
        and processor.get("schema") == sword.processor.SCHEMA
        and processor.get("status") == "named-direct-members-exact-span"
        and processor.get("source") == source and processor.get("logicalSha256") == logical_sha256
        and [processor.get("start"), processor.get("end")] == selected["processor"]
        and processor.get("unionTag") == plan["unionTag"]
        and processor.get("wholeStoredSpanExact") is True and processor.get("recursiveNamedSchemaExact") is True
        and [row.get("name") for row in named] == [row["name"] for row in plan["fieldPlan"]]
        and [enable.get("start"), enable.get("end")] == selected["enableSide"]
        and enable.get("declaredType") == contract["parentTypedChildren"][-1]["typeName"]
        and enable.get("recursiveNamedSchemaExact") is True and side_valid
    )


def validate_receipt(receipt: Any, *, route: str, source: str, length: int,
                     logical_sha256: str) -> None:
    """Check complete named composition while retaining diagnostic scope flags."""
    if route not in ROUTES:
        gate._fail("buff-selected-root-route", source=source, expected=list(ROUTES), actual=route)
    contract = _contracts()[route]
    selected = contract["selectedSource"]
    if (source != selected["path"] or length != selected["length"] or logical_sha256 != selected["sha256"]):
        gate._fail("buff-selected-root-source-identity", source=source,
                   expected={key: selected[key] for key in ("path", "length", "sha256")},
                   actual={"path": source, "length": length, "sha256": logical_sha256})
    fields = receipt.get("fields") if isinstance(receipt, Mapping) else None
    root_fields = root._native_contract()["fields"]
    if (not isinstance(receipt, Mapping) or receipt.get("schema") != ROUTES[route][3]
            or receipt.get("status") != "named-exact-full" or receipt.get("wholeSchemaExact") is not True
            or receipt.get("selectedOnly") is not True or receipt.get("publicationEligible") is not False
            or receipt.get("nativeStatus") != "validated" or receipt.get("source") != source
            or receipt.get("logicalSha256") != logical_sha256 or receipt.get("rootMemberCount") != 30
            or receipt.get("headerRange") != [0, 1] or receipt.get("physicalEof") != length
            or receipt.get("bytesConsumed") != length or not isinstance(fields, list) or len(fields) != 30
            or any(not isinstance(field, Mapping) for field in fields)
            or [field.get("index") for field in fields] != list(range(30))
            or [field.get("name") for field in fields] != [field["name"] for field in root_fields]
            or fields[0].get("start") != 1
            or any(type(field.get("start")) is not int or type(field.get("end")) is not int
                   or field["end"] <= field["start"] for field in fields)
            or any(left["end"] != right["start"] for left, right in zip(fields, fields[1:]))
            or fields[-1]["end"] != length or fields[15].get("value") != PurePosixPath(source).stem):
        gate._fail("buff-selected-root-receipt-incomplete", source=source,
                   expected="source-bound diagnostic proof with 30 contiguous named fields, ID and EOF", actual=route)
    if ((fields[4].get("child") or {}).get("status") != "exact-datapair-list"
            or (fields[4].get("child") or {}).get("consumedEnd") != fields[4]["end"]
            or fields[10].get("count") not in (-1, 0) and (
                (fields[10].get("child") or {}).get("status") != "exact"
                or (fields[10].get("child") or {}).get("consumedEnd") != fields[10]["end"])):
        gate._fail("buff-selected-root-common-child-incomplete", source=source,
                   expected="exact DataPair and GlobalModifier endpoints", actual=route)
    if route == "positiveHeal":
        child = fields[13].get("child") or {}
        condition = child.get("condition") or {}
        complete = (child.get("status") == "selected-heal-processor-named-exact"
                    and (child.get("healModifier") or {}).get("wholeNamedSchemaExact") is True
                    and (child.get("processor") or {}).get("wholeStoredSchemaExact") is True
                    and (condition.get("condition") or {}).get("wholeNamedSchemaExact") is True
                    and (condition.get("action") or {}).get("wholeNamedSchemaExact") is True)
    elif route == "breakPassing":
        child = fields[5].get("child") or {}
        complete = (child.get("status") == "exact-selected-buff-event-action"
                    and all((child.get(key) or {}).get("wholeNamedSchemaExact") is True
                            for key in ("buffEventAction", "map", "sequence", "action")))
    elif route == "emptyConditionTagTen":
        child = fields[6].get("child") or {}
        damage = child.get("damageModifier") or {}
        complete = (child.get("status") == "exact-selected-empty-condition-tag-ten"
                    and (fields[3].get("child") or {}).get("wholeNamedSchemaExact") is True
                    and damage.get("wholeNamedSchemaExact") is True
                    and (damage.get("conditionChild") or {}).get("status") == "exact-empty-sequence"
                    and (damage.get("conditionChild") or {}).get("wholeStoredSpanExact") is True
                    and (damage.get("processorChild") or {}).get("recursiveNamedSchemaExact") is True
                    and (damage.get("processorChild") or {}).get("wholeStoredSpanExact") is True)
    else:
        complete = _sword_receipt_complete(fields[6], contract=contract, source=source,
                                          logical_sha256=logical_sha256)
    if not complete:
        gate._fail("buff-selected-root-child-incomplete", source=source,
                   expected="every selected positive child recursively named", actual=route)


def admit_current_source(data: bytes, *, source: str, logical_sha256: str,
                         outer_row: dict[str, Any], root_validation: Mapping[str, Any],
                         context: Mapping[str, Any]) -> dict[str, Any] | None:
    matches = [name for name, contract in context["contracts"].items()
               if contract["selectedSource"]["path"] == source]
    if not matches:
        return None
    if len(matches) != 1:
        gate._fail("buff-selected-root-overlapping-selection", source=source, actual=matches)
    route = matches[0]
    selected = context["contracts"][route]["selectedSource"]
    if len(data) != selected["length"] or logical_sha256 != selected["sha256"]:
        return {"branch": route, "diagnostic": {
            "code": "buff-selected-root-source-identity", "source": source,
            "expected": {key: selected[key] for key in ("length", "sha256")},
            "actual": {"length": len(data), "sha256": logical_sha256},
        }}
    if any(outer_row.get(key) is not None for key in OLD_RECEIPTS):
        gate._fail("buff-selected-root-overlapping-receipt", source=source,
                   expected="one exclusive full-root proof", actual=route)
    _selected_native(route, selected, root_validation, context["validations"][route])
    if hashlib.sha256(data).hexdigest().upper() != logical_sha256:
        gate._fail("buff-selected-root-logical-hash", source=source,
                   expected=logical_sha256, actual=hashlib.sha256(data).hexdigest().upper())
    _module, decode, argument, _schema = ROUTES[route]
    try:
        receipt = decode(data, source=source, expected_sha256=logical_sha256,
                         native_validation=root_validation, outer_row=outer_row,
                         **{argument: context["validations"][route]})
    except (ValueError, KeyError, IndexError, OverflowError) as exc:
        gate._fail("buff-selected-root-forward-reader", source=source,
                   expected=f"complete {route} selected root through physical EOF",
                   actual=f"{type(exc).__name__}: {exc}"[:400])
    validate_receipt(receipt, route=route, source=source, length=len(data), logical_sha256=logical_sha256)
    return {"branch": route, "receipt": receipt}


def validate_recorded_row(row: Mapping[str, Any], *, root_validation: Mapping[str, Any],
                          selected_validations: Mapping[str, Any]) -> None:
    route = row.get("rootSelectedSourceBranch")
    identity = row.get("identity") or {}
    source = identity.get("virtualPath")
    if (route not in ROUTES or row.get("rootSelectedSourceCandidate") is not True
            or any(row.get(key) is not None for key in OLD_RECEIPTS)
            or row.get("rootNoPositiveCandidate") is True
            or row.get("rootPositiveDamageCandidate") is True
            or row.get("rootSingleCreateActionCandidate") is True):
        gate._fail("buff-selected-root-recorded-branch", source=str(source),
                   expected="one exclusive selected-source candidate/receipt", actual=route)
    selected = _contracts()[route]["selectedSource"]
    _selected_native(route, selected, root_validation, selected_validations.get(route) or {})
    validate_receipt(row.get("rootSelectedSourceReceipt"), route=route, source=source,
                     length=identity.get("length"), logical_sha256=row.get("logicalSha256"))


def replay_recorded_source(data: bytes, *, outer_row: dict[str, Any],
                           root_validation: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    route = outer_row["rootSelectedSourceBranch"]
    source = outer_row["identity"]["virtualPath"]
    # The original anonymous outer candidates remain evidence for the selected
    # child endpoint. The complete family receipt does not replace those frames.
    replay = admit_current_source(data, source=source, logical_sha256=outer_row["logicalSha256"],
                                  outer_row=outer_row, root_validation=root_validation, context=context)
    expected_digest = canonical_json_sha256(outer_row["rootSelectedSourceReceipt"])
    actual_digest = canonical_json_sha256(replay["receipt"]) if replay is not None and "receipt" in replay else None
    if replay is None or replay.get("branch") != route or actual_digest != expected_digest:
        gate._fail("buff-selected-root-canonical-replay", source=source,
                   expected={"receiptSha256": expected_digest, "logicalSha256": outer_row["logicalSha256"]},
                   actual={"receiptSha256": actual_digest, "branch": route})
    return replay["receipt"]


def summarize(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {route: {
        "candidates": sum(row.get("rootSelectedSourceBranch") == route for row in rows),
        "wholeSchemaExact": sum(row.get("rootSelectedSourceBranch") == route
                                and row.get("rootSelectedSourceReceipt") is not None for row in rows),
        "logicalBytes": sum(row["identity"]["length"] for row in rows
                            if row.get("rootSelectedSourceBranch") == route
                            and row.get("rootSelectedSourceReceipt") is not None),
        "boundary": "One reviewed logical path/length/SHA with current named root/child replay; live behavior remains unobserved.",
    } for route in ROUTES}
