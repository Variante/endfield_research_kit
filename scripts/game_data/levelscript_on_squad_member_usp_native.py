"""Authenticate the squad-USP header and its registered default stored children.

Runtime provider replacement and execution remain unresolved.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import (
    generic_method_candidates, relative_branch_target, usage_method_spec,
)
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image

SCHEMA = "endfield.levelscript-on-squad-member-usp-reach-max-native.v2"
LABEL = "levelscriptOnSquadMemberUspNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_on_squad_member_usp_native.json"
MANAGED_TYPE = "Beyond.Gameplay.Actions.LevelEvent.OnSquadMemberUspReachMax"
_CHILD_TYPES = {
    "Param<bool>": "Beyond.Gameplay.Actions.Param`1<bool>",
    "ParamOutput<EntityPtr>": "Beyond.Gameplay.Actions.ParamOutput`1<Beyond.Gameplay.Core.EntityPtr>",
    "ParamOutput<float>": "Beyond.Gameplay.Actions.ParamOutput`1<float>",
}


class SquadUspNativeError(ValueError):
    def __init__(self, check: str, expected: Any, actual: Any, **location: Any):
        self.check, self.expected, self.actual, self.location = check, expected, actual, location
        super().__init__(f"{LABEL}.{check}: expected={str(expected)[:240]}, actual={str(actual)[:240]}, location={location}")


def _require(check: str, expected: Any, actual: Any, **location: Any) -> None:
    if actual != expected:
        raise SquadUspNativeError(check, expected, actual, **location)


def _signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


@lru_cache(maxsize=4)
def _read(path: Path, signature: tuple[int, int]) -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(path, schema=SCHEMA, status="exact-current-build", label=LABEL)
    route, parent = contract["route"], contract["parentEvidence"]
    _require("managed-type", MANAGED_TYPE, route["typeName"])
    _require("family", "ActionHeader", route["family"])
    _require("member-count", 16, route["serializedMemberCount"])
    _require("inherited-members", 14, route["inheritedMemberCount"])
    _require("field-count", route["serializedMemberCount"], len(route["fields"]))
    _require("child-kinds", list(_CHILD_TYPES), [row["kind"] for row in contract["children"]])
    _require("typed-tail", [["validate", "Param<bool>"], ["squadMemeber", "ParamOutput<EntityPtr>"],
                            ["uspValue", "ParamOutput<float>"]], route["fields"][13:])
    _require("parent-status", "exact-default-stored", parent["status"])
    _require("positive-default-admission", True, parent["positiveChildrenAdmission"])
    _require("null-default-admission", True, parent["nullChildrenAdmission"])
    _require("outer-null-admission", True, parent["outerWrapperNullAdmission"])
    _require("typed-read-context-order", list(range(13, 16)), [row["memberIndex"] for row in route["paramContexts"]])
    _require("ordered-read-indices", list(range(16)), [row["memberIndex"] for row in route["orderedReads"]])
    _require("ordered-read-fields", [row[0] for row in route["fields"]], [row["fieldName"] for row in route["orderedReads"]])
    for row in contract["children"]:
        _require("child-managed-type", _CHILD_TYPES[row["kind"]], row["managedType"])
        expected = [["constValue", "bool"], ["idRef", "int32"], ["paramSource", "int32"], ["path", "string"]] if row["kind"] == "Param<bool>" else [["paramTarget", "int32"], ["path", "string"]]
        _require("child-field-shape", expected, row["fields"], child=row["kind"])
        _require("child-member-count", len(expected), row["memberCount"], child=row["kind"])
        _require("child-default-join", "exact-default-stored", row["parentProviderJoin"], child=row["kind"])
    return contract


def read_on_squad_member_usp_contract(contract_path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    """Read route identity only; callers still authenticate before consuming bytes."""
    path = Path(contract_path)
    return _read(path, _signature(path))


def _instruction(image: Any, rva: int, expected_hex: str) -> bytes:
    expected = bytes.fromhex(expected_hex)
    actual = image.pe.bytes_at_va(image.pe.image_base + rva, len(expected))
    _require("instruction-window", expected.hex().upper(), actual.hex().upper(), instructionRva=rva)
    return actual


def _branch(image: Any, row: list[Any]) -> None:
    rva, raw_hex, target = row
    raw = _instruction(image, rva, raw_hex)
    actual = relative_branch_target(raw, image.pe.image_base + rva, source=LABEL) - image.pe.image_base
    _require("branch-target", target, actual, instructionRva=rva)


def _method(image: Any, row: list[Any]) -> None:
    method = image.metadata.methods[row[0]]
    actual = [row[0], image.type_name(method.declaring_type), image.metadata.string(method.name_index),
              image.method_pointer_va(method) - image.pe.image_base]
    _require("method-row", row, actual, methodIndex=row[0])


def _windows(image: Any, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        actual = hashlib.sha256(image.window_bytes(row)).hexdigest().upper()
        _require("code-window-sha256", row["sha256"].upper(), actual, startRva=row["startRva"], endRva=row["endRva"])


def _complete_windows(image: Any, body: BodyIndex, methods: list[list[Any]], windows: list[dict[str, Any]]) -> None:
    expected = []
    for method in methods:
        _method(image, method)
        pointer = image.pe.image_base + method[3]
        expected.append([method[3], body.extents[pointer] - image.pe.image_base])
        expected.extend([[start - image.pe.image_base, start + size - image.pe.image_base]
                         for start, size in body.chained_fragments.get(pointer, [])])
    _require("complete-owned-method-windows", expected, [[row["startRva"], row["endRva"]] for row in windows])
    _windows(image, windows)


def _in_windows(rva: int, size: int, windows: list[dict[str, Any]]) -> bool:
    return any(row["startRva"] <= rva and rva + size <= row["endRva"] for row in windows)


def _validate_outer_null(image: Any, route: dict[str, Any], helpers: list[dict[str, Any]]) -> None:
    """Authenticate the direct FF branch without admitting nested providers."""
    proof = route["outerNullProof"]
    call = proof["objectHeaderCall"]
    helper = next(row for row in helpers if row["readKind"] == "object-header")
    _require("outer-null-helper", helper["rva"], call[2])
    _branch(image, call)
    for key in ("falseTest", "falseBranch", "nullOutputStore"):
        row = proof[key]
        raw = _instruction(image, *row)
        _require("outer-null-parent-window", True, _in_windows(row[0], len(raw), route["codeWindows"]), instruction=key)
    _require("outer-null-test", "84C0", proof["falseTest"][1])
    _require("outer-null-test-placement", call[0] + 5, proof["falseTest"][0])
    _require("outer-null-branch-placement", proof["falseTest"][0] + 2, proof["falseBranch"][0])
    branch = bytes.fromhex(proof["falseBranch"][1])
    _require("outer-null-branch-opcode", "0F84", branch[:2].hex().upper())
    _require("outer-null-branch-size", 6, len(branch))
    _require("outer-null-branch-target", proof["nullOutputStore"][0],
             proof["falseBranch"][0] + 6 + struct.unpack_from("<i", branch, 2)[0])
    _require("outer-null-clear-output", "48832300", proof["nullOutputStore"][1])
    for key, expected in (("helperCursorAdvance", "48FF4350"), ("helperFFCompare", "803EFF"),
                          ("helperReturnSetNotEqual", "0F95C0")):
        row = proof[key]
        raw = _instruction(image, *row)
        _require("outer-null-helper-instruction", expected, row[1], instruction=key)
        _require("outer-null-helper-window", True, _in_windows(row[0], len(raw), helper["codeWindows"]), instruction=key)
    _require("outer-null-helper-order", True, proof["helperCursorAdvance"][0] < proof["helperFFCompare"][0]
             < proof["helperReturnSetNotEqual"][0])


def _validate_context(image: Any, context: dict[str, Any], expected_type: str, spec_bytes: bytes,
                      generic_table: bytes, code: dict[str, Any]) -> None:
    field = context["fieldName"]
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    spec = usage_method_spec(usage, spec_bytes, len(image.metadata.methods), image.registration["genericInstsCount"],
                             source=LABEL, usage_offset=cell, records_offset=int(image.registration["methodSpecs"], 16))
    _require("typed-read-method-spec", context["methodSpec"], spec, field=field, instructionRva=context["instructionRva"])
    method = image.metadata.methods[spec["definition"]]
    _require("typed-reader-owner", "MemoryPack.MemoryPackReader", image.type_name(method.declaring_type), field=field)
    _require("typed-reader-name", "ReadValue", image.metadata.string(method.name_index), field=field)
    _require("typed-reader-no-class-instantiation", -1, spec["classInstantiationIndex"], field=field)
    instance = image.instantiations.resolve(spec["methodInstantiationIndex"])
    args = [runtime_type_name(image.pe, image.metadata, arg.type_pointer_va) for arg in instance.arguments]
    _require("typed-read-argument", [expected_type], args, field=field)
    _require("reviewed-typed-read-argument", context["methodArguments"], args, field=field)
    _require("typed-read-raw-argument", [context["argumentRawHex"]], [arg.raw_type_record_hex for arg in instance.arguments], field=field)
    raw = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
    _require("typed-read-generic-kind", 0x15, raw[10], field=field)
    carrier = context["classCarrier"]
    address = struct.unpack_from("<Q", raw)[0]
    actual_carrier = image.pe.bytes_at_va(address, 32)
    _require("generic-carrier-pointer", carrier["pointerVa"], address, field=field)
    _require("generic-carrier-bytes", carrier["rawHex"], actual_carrier.hex().upper(), field=field)
    base_pointer, class_pointer = struct.unpack_from("<QQ", actual_carrier)
    _require("generic-base-pointer", carrier["baseTypePointerVa"], base_pointer, field=field)
    base_raw = image.pe.bytes_at_va(base_pointer, 16)
    _require("generic-base-bytes", carrier["baseRawHex"], base_raw.hex().upper(), field=field)
    _require("generic-base-definition", carrier["baseDefinition"], struct.unpack_from("<Q", base_raw)[0], field=field)
    _require("generic-base-name", carrier["baseTypeName"], image.type_name(carrier["baseDefinition"]), field=field)
    _require("generic-class-pointer", carrier["classInstantiationPointerVa"], class_pointer, field=field)
    child = image.instantiations.resolve_pointer(class_pointer)
    _require("generic-class-index", carrier["classInstantiationIndex"], child.index, field=field)
    _require("generic-child-raw", carrier["argumentRawHex"], [arg.raw_type_record_hex for arg in child.arguments], field=field)
    _require("generic-child-names", carrier["arguments"], [runtime_type_name(image.pe, image.metadata, arg.type_pointer_va) for arg in child.arguments], field=field)
    candidates = generic_method_candidates(generic_table, image.registration["genericMethodTableCount"],
        image.registration["methodSpecsCount"], {spec["index"]}, code["genericMethodPointersCount"],
        code["invokerPointersCount"], source=LABEL, offset=int(image.registration["genericMethodTable"], 16))
    resolved = [{"row": row, "rva": image.pe.u64_at_va(int(code["genericMethodPointers"], 16) + row["indices"][0] * 8) - image.pe.image_base} for row in candidates]
    _require("registered-generic-candidates", context["genericCandidates"], resolved, field=field)
    _branch(image, [context["callRva"], context["callHex"], context["targetRva"]])


def _validate(image: Any, contract: dict[str, Any]) -> dict[str, Any]:
    base, route = image.pe.image_base, contract["route"]
    body, wrappers = BodyIndex(image), derive_from_image(image)
    switch = read_union_switch(image, "Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", wrappers=wrappers)
    dispatcher = contract["dispatcher"]
    _require("dispatcher-count", dispatcher["entryCount"], switch["entryCount"])
    _require("dispatcher-table", base + dispatcher["tableRva"], int(switch["tableVa"], 16))
    table = image.pe.bytes_at_va(base + dispatcher["tableRva"], dispatcher["entryCount"] * 4)
    _require("dispatcher-table-sha256", dispatcher["tableSha256"], hashlib.sha256(table).hexdigest().upper())
    selected = switch["entries"][route["tag"]]
    for expected_name, actual_name in (("wrapperName", "wrapperName"), ("typeDefinition", "typeDefinition"), ("registeredTypeIndex", "registeredTypeIndex")):
        _require("dispatcher-" + expected_name, route[expected_name], selected[actual_name])
    for name, actual_name in (("switchTargetRva", "targetVa"), ("bodyRva", "bodyVa"), ("usageCellRva", "usageCellVa")):
        _require("dispatcher-" + name, base + route[name], int(selected[actual_name], 16))
    _require("dispatcher-usage-bytes", route["usageRawHex"], image.pe.bytes_at_va(base + route["usageCellRva"], 8).hex().upper())
    wrapper = wrappers[route["typeDefinition"]]
    _require("wrapped-managed-type", route["typeName"], wrapper.wrapped_type)
    _require("generated-parent-declarations", route["nativeDeclaredTypes"], [[member.name, member.declared_type] for member in wrapper.members])
    _require("generated-parent-inheritance", route["inheritedMemberCount"], len(wrapper.inherited_members))
    _complete_windows(image, body, route["methods"], route["codeWindows"])
    count = _instruction(image, *route["memberCountInstruction"])
    _require("parent-member-count-compare", bytes.fromhex("807C2438") + bytes((route["serializedMemberCount"],)), count)
    _branch(image, route["formatterForwardingJump"])
    _validate_outer_null(image, route, contract["sourceHelpers"])
    primitive_helpers = {row["readKind"]: row["rva"] for row in contract["sourceHelpers"]}
    previous = route["memberCountInstruction"][0]
    for read, member in zip(route["orderedReads"], wrapper.members):
        _require("ordered-read-wire", route["fields"][read["memberIndex"]][1], read["wire"], field=read["fieldName"])
        if read["wire"] in ("bool", "int32", "string"):
            _require("primitive-read-helper", primitive_helpers[read["wire"]], read["readTargetRva"], field=read["fieldName"])
        _require("ordered-read-setter-order", True, previous < read["readCallRva"] < read["setterCallRva"], field=read["fieldName"])
        _branch(image, [read["readCallRva"], read["readCallHex"], read["readTargetRva"]])
        _branch(image, [read["setterCallRva"], read["setterCallHex"], read["setterTargetRva"]])
        _method(image, read["setterMethod"])
        _require("generated-setter-index", read["setterMethod"][0], member.method_index, field=read["fieldName"])
        _require("generated-setter-type", read["setterDeclaredType"], member.declared_type, field=read["fieldName"])
        _require("generated-setter-owner", read["declaringWrapper"], member.declaring_wrapper, field=read["fieldName"])
        previous = read["setterCallRva"]
    reg, pe = image.registration, image.pe
    spec_bytes = pe.bytes_at_va(int(reg["methodSpecs"], 16), reg["methodSpecsCount"] * 12)
    generic_table = pe.bytes_at_va(int(reg["genericMethodTable"], 16), reg["genericMethodTableCount"] * 16)
    code = image.mapper.code_registration_summary(pe, image.code_registration)
    for context in route["paramContexts"]:
        read = route["orderedReads"][context["memberIndex"]]
        _require("typed-context-field", read["fieldName"], context["fieldName"], field=context["fieldName"])
        _require("typed-context-read-call", [read["readCallRva"], read["readCallHex"], read["readTargetRva"]],
                 [context["callRva"], context["callHex"], context["targetRva"]], field=context["fieldName"])
        _require("typed-context-placement", True, route["orderedReads"][context["memberIndex"] - 1]["setterCallRva"] < context["instructionRva"] < read["readCallRva"], field=context["fieldName"])
        _validate_context(image, context, _CHILD_TYPES[route["fields"][context["memberIndex"]][1]], spec_bytes, generic_table, code)
    for child in contract["children"]:
        wrapper = wrappers[child["wrapperTypeDefinition"]]
        _require("child-instance-type", child["managedType"], wrapper.wrapped_type, child=child["kind"])
        _require("child-wrapper-name", child["wrapperName"], wrapper.name, child=child["kind"])
        _require("child-member-declarations", [[row["name"], row["declaredType"]] for row in child["setters"]], [[row.name, row.declared_type] for row in wrapper.members], child=child["kind"])
        _complete_windows(image, body, child["methods"], child["codeWindows"])
        count = _instruction(image, *child["memberCountInstruction"])
        expected_opcode = bytes.fromhex("4080FD" if child["kind"] == "Param<bool>" else "4080FE")
        _require("child-member-count-compare", expected_opcode + bytes((child["memberCount"],)), count, child=child["kind"])
        _branch(image, child["forwardingJump"])
        for call in child["sourceCalls"] + child.get("setterCalls", []):
            _branch(image, call)
        for store in child.get("fieldStores", []):
            _instruction(image, *store[:2])
        if child.get("nullBranch"):
            _instruction(image, *child["nullBranch"])
        for setter in child["setters"]:
            _complete_windows(image, body, [setter["method"]], setter["codeWindows"])
    for helper in contract["sourceHelpers"]:
        expected = [[helper["rva"], body.extents[base + helper["rva"]] - base],
                    *[[start - base, start + size - base] for start, size in body.chained_fragments.get(base + helper["rva"], [])]]
        _require("source-helper-owned-extents", expected, [[w["startRva"], w["endRva"]] for w in helper["codeWindows"]])
        _windows(image, helper["codeWindows"])
    for candidate in contract["constructorTypePairCandidates"]:
        raw = spec_bytes[candidate["index"] * 12:candidate["index"] * 12 + 12]
        _require("constructor-pair-method-spec", candidate["spec"], list(struct.unpack("<iii", raw)))
        method = image.metadata.methods[candidate["spec"][0]]
        _require("constructor-pair-owner", candidate["owner"], image.type_name(method.declaring_type))
        _require("constructor-pair-method", candidate["method"], image.metadata.string(method.name_index))
        instance = image.instantiations.resolve(candidate["spec"][1])
        _require("constructor-pair-arguments", candidate["args"], [runtime_type_name(pe, image.metadata, arg.type_pointer_va) for arg in instance.arguments])
    composition = contract["defaultComposition"]
    validate_registered_formatter_composition(image, composition, label=LABEL)
    registered = {row["originalType"]: row for row in composition["registrations"]}
    for context in route["paramContexts"]:
        expected_type = _CHILD_TYPES[route["fields"][context["memberIndex"]][1]]
        argument = image.instantiations.resolve(context["methodSpec"]["methodInstantiationIndex"]).arguments[0]
        registration = registered[expected_type]
        original = image.instantiations.resolve(registration["classInstantiation"]).arguments[0]
        _require("parent-default-original-pointer", original.type_pointer_va, argument.type_pointer_va, field=context["fieldName"])
    return {"typedReadsChecked": len(route["paramContexts"]), "isolatedChildrenChecked": len(contract["children"]),
            "parentProviderJoinStatus": "exact-default-stored", "positiveChildrenAdmission": True, "nullChildrenAdmission": True, "runtimeProviderSelection": "unresolved",
            "outerWrapperNullAdmission": True}


@lru_cache(maxsize=4)
def _authenticate(path: Path, signature: tuple[int, int], gameassembly: Path, ga_signature: tuple[int, int],
                  metadata: Path, metadata_signature: tuple[int, int]) -> dict[str, Any]:
    return _validate(open_native_image(gameassembly, metadata), _read(path, signature))


def load_on_squad_member_usp_contract(*, game_root: Path | None = None,
        gameassembly: Path | None = None, metadata: Path | None = None,
        contract_path: Path = DEFAULT_CONTRACT) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return isolated/static facts only after selected native inputs authenticate."""
    path, audit = Path(contract_path), {"validator": LABEL, "source": str(contract_path), "claims": {}}
    try:
        signature = _signature(path)
        contract = _read(path, signature)
        expected = contract["nativeInputs"]
        root = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"],
            gameassembly=Path(gameassembly) if gameassembly is not None else (root.parent / "GameAssembly.dll" if root else None),
            metadata=Path(metadata) if metadata is not None else (root / "il2cpp_data/Metadata/global-metadata.dat" if root else None))
        audit["nativeSources"] = {"GameAssembly.dll": str(getattr(gate, "gameassembly", gameassembly or "unresolved")),
                                  "global-metadata.dat": str(getattr(gate, "metadata", metadata or "unresolved"))}
        if gate.status != "validated":
            return {}, {**audit, "status": gate.status, "failedCheck": "installed-native-inputs", "detail": gate.detail,
                        "validationFailures": [{"check": "installed-native-inputs", "expected": "validated selected native hashes", "actual": gate.status, "detail": gate.detail}]}
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        if not unity.is_file():
            raise SquadUspNativeError("UnityPlayer.dll", "selected adjacent file", "missing")
        _require("UnityPlayer.dll-sha256", expected["UnityPlayer.dll"], sha256_file(unity).upper())
        ga_signature, metadata_signature = _signature(gate.gameassembly), _signature(gate.metadata)
        checked = _authenticate(path, signature, gate.gameassembly, ga_signature, gate.metadata, metadata_signature)
        for label, target, before in (("contract-unchanged", path, signature), ("gameassembly-unchanged", gate.gameassembly, ga_signature), ("metadata-unchanged", gate.metadata, metadata_signature)):
            _require(label, before, _signature(target))
        return contract, {**audit, "status": "validated", "evidenceBoundary": "direct", "claims": contract["evidenceBoundaryByClaim"], **checked}
    except (OSError, ValueError, KeyError, TypeError, IndexError, RuntimeError) as error:
        failure = {"check": getattr(error, "check", "contract-or-native"), "expected": str(getattr(error, "expected", "authenticated static/isolated facts"))[:500],
                   "actual": str(getattr(error, "actual", error))[:500], "location": getattr(error, "location", {}),
                   "nativeSources": audit.get("nativeSources", {})}
        return {}, {**audit, "claims": {}, "status": "validation_failed", "failedCheck": failure["check"],
                    "detail": str(error)[:500], "validationFailures": [failure]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args(argv)
    _, audit = load_on_squad_member_usp_contract(game_root=args.game_root, gameassembly=args.gameassembly, metadata=args.metadata)
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
