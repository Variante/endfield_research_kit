"""Authenticate the stored FacChangeBuildingTemplate ActionBase route.

This proves the selected native reader, typed parameter contexts and current
source cursors. It does not prove a live facility-template change.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp import protocol
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import (
    generic_type_carrier, method_spec_record, method_spec_usage_index,
    unresolved_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-fac-change-building-native-contract.v1"
LABEL = "levelscriptFacChangeBuildingNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_fac_change_building_native.json"
_PARAM_ELEMENTS = {
    "Param<bool>": ("System.Boolean", "bool", 2),
    "Param<float>": ("System.Single", "float", 12),
    "Param<string>": ("System.String", "string", 14),
    "Param<int>": ("System.Int32", "int", 8),
    "Param<FCNodeMode>": ("Beyond.GEnums.FCNodeMode", "Beyond.GEnums.FCNodeMode", 0x11),
}


def _contract(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_bytes())
    route = data.get("route", {})
    fields = route.get("fields", [])
    reads = data.get("orderedReads", [])
    setters = data.get("ownSetters", [])
    contexts = data.get("nestedContexts", [])
    if (
        data.get("schema") != SCHEMA
        or data.get("status") != "exact-current-build"
        or data.get("evidenceBoundary") != "exact"
        or route.get("family") != "ActionBase"
        or route.get("tag") != 0xC4
        or route.get("typeName") != "Beyond.Gameplay.Actions.FacChangeBuildingTemplate"
        or route.get("serializedMemberCount") != 14
        or route.get("inheritedMemberCount") != 8
        or len(fields) != 14 or len(route.get("nativeDeclaredTypes", [])) != 14
        or fields[8:] != [
            ["instKey", "Param<string>"],
            ["level", "Param<int>"],
            ["mode", "Param<FCNodeMode>"],
            ["newTemplateName", "Param<string>"],
            ["playBuildEffect", "Param<bool>"],
            ["playBuildEffectDuration", "Param<float>"],
        ]
        or [row.get("memberIndex") for row in reads] != list(range(14))
        or [[row.get("fieldName"), row.get("readKind")] for row in reads] != fields
        or [row[0] for row in route["nativeDeclaredTypes"]] != [row[0] for row in fields]
        or set(data.get("readerHelpers", {})) != {kind for _, kind in fields}
        or [row.get("memberIndex") for row in setters] != [8, 9, 10, 11, 12, 13]
        or [row.get("memberIndex") for row in contexts] != [8, 9, 10, 11, 12, 13]
        or [(row.get("elementTypeName"), row.get("elementTypeKind")) for row in contexts]
        != [(_PARAM_ELEMENTS[kind][0], _PARAM_ELEMENTS[kind][2]) for _, kind in fields[8:]]
        or any(row.get("baseTypeName") != "Beyond.Gameplay.Actions.Param`1" for row in contexts)
        or len(data.get("methods", [])) != 2
        or len(data.get("codeWindows", [])) != 2
        or data.get("enumUnderlying", {}).get("typeDefinition") != contexts[2].get("elementTypeDefinition")
        or data.get("enumUnderlying", {}).get("typeName") != "Beyond.GEnums.FCNodeMode"
        or data.get("enumUnderlying", {}).get("underlyingType") != "int"
        or not data.get("enumUnderlying", {}).get("members")
        or not data.get("sourceReceipts")
        or any(len(row) != 5 for row in data["sourceReceipts"])
        or len({(row[0], row[2]) for row in data["sourceReceipts"]}) != len(data["sourceReceipts"])
        or bytes.fromhex(data["memberCountInstruction"]["hex"])[-1] != 14
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return data


def _call_target(image: Any, rva: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:call={rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_context(image: Any, context: dict[str, Any], kind: str) -> None:
    member = context["memberIndex"]
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    spec_index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if spec_index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:param-spec-index={member}")
    address = int(image.registration["methodSpecs"], 16) + spec_index * 12
    spec = method_spec_record(
        image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source=LABEL, offset=address,
    )
    method = image.metadata.methods[spec[0]]
    if (
        list(spec) != context["methodSpec"]
        or image.type_name(method.declaring_type) != "MemoryPack.MemoryPackReader"
        or image.metadata.string(method.name_index) != "ReadValue"
    ):
        raise ValueError(f"{LABEL}.native:param-spec={member}")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:param-arity={member}")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"].upper() or raw[10] != context["typeKind"] != 0x15:
        raise ValueError(f"{LABEL}.native:param-argument={member}")
    carrier_pointer = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(carrier_pointer, 32)
    base_raw = image.pe.bytes_at_va(struct.unpack_from("<Q", carrier_raw)[0], 16)
    carrier = generic_type_carrier(
        raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
        type_count=len(image.metadata.types), source=LABEL,
    )
    if (
        carrier != context["classCarrier"]
        or image.type_name(carrier["baseDefinitionIndex"]) != "Beyond.Gameplay.Actions.Param`1"
    ):
        raise ValueError(f"{LABEL}.native:param-carrier={member}")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    if len(child.arguments) != 1 or child_row != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:param-instantiation={member}")
    element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
    expected_name, runtime_name, expected_kind = _PARAM_ELEMENTS[kind]
    definition = struct.unpack_from("<Q", element)[0] if expected_kind == 0x11 else None
    if (
        element.hex().upper() != context["elementRawHex"].upper()
        or element[10] != context["elementTypeKind"] != expected_kind
        or context["elementTypeName"] != expected_name
        or protocol.runtime_type_name(image.pe, image.metadata, child.arguments[0].type_pointer_va) != runtime_name
        or context["elementTypeDefinition"] != definition
        or (definition is not None and image.type_name(definition) != expected_name)
    ):
        raise ValueError(f"{LABEL}.native:param-element={member}")


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    route = contract["route"]
    branch = contract["dispatcher"]
    base = image.pe.image_base
    wrappers = derive_from_image(image)
    switch = read_union_switch(
        image, "Beyond_Gameplay_Actions_ActionBaseForMemoryPack", wrappers=wrappers,
    )
    tag = route["tag"]
    if (
        switch["entryCount"] != branch["switchEntryCount"]
        or int(switch["tableVa"], 16) != base + branch["switchTableRva"]
        or not 0 <= tag < switch["entryCount"]
    ):
        raise ValueError(f"{LABEL}.native:switch-shape")
    table = image.pe.bytes_at_va(base + branch["switchTableRva"], switch["entryCount"] * 4)
    if hashlib.sha256(table).hexdigest().upper() != branch["switchTableSha256"].upper():
        raise ValueError(f"{LABEL}.native:switch-hash")
    entry = switch["entries"][tag]
    target = struct.unpack_from("<I", table, tag * 4)[0]
    jump = image.pe.bytes_at_va(base + target, 5)
    if (
        target != branch["switchTargetRva"] or jump[0] != 0xE9
        or jump.hex().upper() != branch["switchEntryHex"].upper()
        or target + 5 + struct.unpack_from("<i", jump, 1)[0] != branch["bodyRva"]
        or int(entry["targetVa"], 16) != base + target
        or int(entry["bodyVa"], 16) != base + branch["bodyRva"]
        or entry["wrapperName"] != route["wrapperName"]
        or entry["typeDefinition"] != route["typeDefinition"]
        or entry["registeredTypeIndex"] != route["registeredTypeIndex"]
    ):
        raise ValueError(f"{LABEL}.native:dispatch-entry")
    if branch["branchWindow"]["startRva"] != branch["bodyRva"]:
        raise ValueError(f"{LABEL}.native:branch-range")
    image.check_windows([branch["branchWindow"]], label=LABEL)
    load_site = branch["typeLoadRva"]
    if not branch["bodyRva"] <= load_site <= branch["branchWindow"]["endRva"] - 7:
        raise ValueError(f"{LABEL}.native:type-load-range")
    load = image.pe.bytes_at_va(base + load_site, 7)
    if load[:3] != b"\x48\x8b\x15" or load.hex().upper() != branch["typeLoadHex"].upper():
        raise ValueError(f"{LABEL}.native:type-load")
    usage_cell = base + load_site + 7 + struct.unpack_from("<i", load, 3)[0]
    usage = image.pe.bytes_at_va(usage_cell, 8)
    index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1, source=LABEL, offset=usage_cell,
    )
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    definition = struct.unpack_from("<Q", image.pe.bytes_at_va(pointer, 16))[0]
    if (
        usage_cell-base != branch["usageCellRva"]
        or usage.hex().upper() != branch["usageRawHex"].upper()
        or index != route["registeredTypeIndex"]
        or definition != route["typeDefinition"]
        or image.type_name(definition) != route["wrapperName"]
    ):
        raise ValueError(f"{LABEL}.native:registered-wrapper")
    wrapper = wrappers[definition]
    normalized = {
        "bool": "bool", "int": "int32", "string": "string",
        "Beyond.GEnums.ScopeName": "int32",
        "Beyond.Gameplay.Actions.Param`1<bool>": "Param<bool>",
        "Beyond.Gameplay.Actions.Param`1<float>": "Param<float>",
        "Beyond.Gameplay.Actions.Param`1<string>": "Param<string>",
        "Beyond.Gameplay.Actions.Param`1<int>": "Param<int>",
        "Beyond.Gameplay.Actions.Param`1<Beyond.GEnums.FCNodeMode>": "Param<FCNodeMode>",
    }
    if (
        wrapper.name != route["wrapperName"]
        or wrapper.wrapped_type != route["typeName"]
        or len(wrapper.members) != 14
        or len(wrapper.inherited_members) != 8
        or len(wrapper.own_members) != 6
        or [[member.name.lstrip("_"), member.declared_type] for member in wrapper.members] != route["nativeDeclaredTypes"]
        or [[member.name.lstrip("_"), normalized.get(member.declared_type)] for member in wrapper.members] != route["fields"]
        or any(member.kind != "enum" or member.underlying_kind != "scalar32" or member.width != 4
               for member in wrapper.members if member.declared_type == "Beyond.GEnums.ScopeName")
    ):
        raise ValueError(f"{LABEL}.native:wrapper-fields")

    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    windows = contract["codeWindows"]
    image.check_windows(windows, label=LABEL)
    image.check_instruction_windows([
        [contract["memberCountInstruction"]["rva"], contract["memberCountInstruction"]["hex"]]
    ], label=LABEL)
    if (
        contract["methods"][0][1] != wrapper.name
        or not contract["methods"][1][1].startswith(wrapper.name + "+")
    ):
        raise ValueError(f"{LABEL}.contract:method-owner")
    reader_ptr = image.method_pointer_va(image.metadata.methods[methods[0]])
    formatter_ptr = image.method_pointer_va(image.metadata.methods[methods[1]])
    body = BodyIndex(image)
    if (
        windows[0]["startRva"] != reader_ptr-base
        or windows[0]["endRva"] != body.extents.get(reader_ptr, 0)-base
        or windows[1]["startRva"] != formatter_ptr-base
        or windows[1]["endRva"] != body.extents.get(formatter_ptr, 0)-base
        or body.chained_fragments.get(reader_ptr)
    ):
        raise ValueError(f"{LABEL}.native:complete-method-windows")
    source_window = windows[0]
    count = contract["memberCountInstruction"]["rva"]
    if not source_window["startRva"] < count < source_window["endRva"]:
        raise ValueError(f"{LABEL}.native:member-count-range")
    previous = count
    for read in contract["orderedReads"]:
        site = read["sourceCallsiteRva"]
        if (
            not previous < site < source_window["endRva"]
            or _call_target(image, site, read["sourceCallHex"]) != read["sourceTargetRva"]
            or read["sourceTargetRva"] != contract["readerHelpers"][read["readKind"]]
        ):
            raise ValueError(f"{LABEL}.native:ordered-read={read['memberIndex']}")
        previous = site
    for setter in contract["ownSetters"]:
        member_index = setter["memberIndex"]
        member = wrapper.members[member_index]
        method_index = setter["methodIndex"]
        method = image.metadata.methods[method_index]
        if (
            member.method_index != method_index
            or member.declaring_wrapper != setter["declaringWrapper"]
            or image.type_name(method.declaring_type) != member.declaring_wrapper
            or image.metadata.string(method.name_index) != setter["setterName"]
            or image.method_pointer_va(method) != base + setter["targetRva"]
            or not contract["orderedReads"][member_index]["sourceCallsiteRva"]
                < setter["callsiteRva"]
                < (contract["orderedReads"][member_index+1]["sourceCallsiteRva"]
                   if member_index+1 < 14 else source_window["endRva"])
            or _call_target(image, setter["callsiteRva"], setter["callHex"]) != setter["targetRva"]
        ):
            raise ValueError(f"{LABEL}.native:setter={member_index}")
    for context in contract["nestedContexts"]:
        member = context["memberIndex"]
        if not (
            contract["orderedReads"][member-1]["sourceCallsiteRva"]
            < context["instructionRva"]
            < contract["orderedReads"][member]["sourceCallsiteRva"]
        ):
            raise ValueError(f"{LABEL}.native:param-context-order={member}")
        _validate_context(image, context, route["fields"][member][1])
    enum = contract["enumUnderlying"]
    enum_type = image.metadata.types[enum["typeDefinition"]]
    value_fields = [field for field in image.metadata.fields_for(enum_type)
                    if image.metadata.string(field.name_index) == "value__"]
    if len(value_fields) != 1 or image.metadata.type_full_name(enum_type) != enum["typeName"]:
        raise ValueError(f"{LABEL}.native:enum-shape")
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + value_fields[0].type_index * 8)
    if protocol.runtime_type_name(image.pe, image.metadata, pointer) != enum["underlyingType"]:
        raise ValueError(f"{LABEL}.native:enum-backing")
    if protocol.native_enum_members(image.metadata, protocol.field_defaults(image.metadata),
                                    image.pe, image.registration, enum["typeName"]) != enum["members"]:
        raise ValueError(f"{LABEL}.native:enum-members")


def _validate_sources(
    contract: dict[str, Any], export_root: Path, ledger_path: Path, summary_path: Path,
) -> int:
    summary = json.loads(summary_path.read_bytes())
    output = summary.get("provenance", {}).get("outputFiles", {})
    if (
        summary.get("status") != "complete"
        or output.get("length") != ledger_path.stat().st_size
        or output.get("sha256", "").upper() != sha256_file(ledger_path).upper()
    ):
        raise ValueError(f"{LABEL}.source:summary-ledger-join")
    ledger: dict[str, dict[str, Any]] = {}
    with gzip.open(ledger_path, "rt", encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData":
                ledger[row["exportRelativePath"]] = row
    if not ledger:
        raise ValueError(f"{LABEL}.source:missing-LevelScript-ledger")
    from scripts.game_data.codecs.levelscript.action_map import _Cursor

    route = contract["route"]
    prefix = bytes((route["tag"], route["serializedMemberCount"]))
    for path, digest, start, end, span_digest in contract["sourceReceipts"]:
        data = (export_root / path).read_bytes()
        if (
            not 0 <= start < end <= len(data)
            or data[start:start+len(prefix)] != prefix
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
            or ledger.get(path, {}).get("length") != len(data)
            or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
        ):
            raise ValueError(f"{LABEL}.source:receipt={path}")
        cursor = _Cursor(data, start)
        tag = cursor.byte("facChangeBuilding.tag")
        if tag != route["tag"] or cursor.byte("facChangeBuilding.memberCount") != 14:
            raise ValueError(f"{LABEL}.source:union-header={path}")
        for name, kind in route["fields"]:
            cursor.value("Param<int>" if kind == "Param<FCNodeMode>" else kind,
                         "facChangeBuilding." + name)
        if cursor.offset != end:
            raise ValueError(f"{LABEL}.source:end-offset={path}")
    return len(contract["sourceReceipts"])


def validate_fac_change_building_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Validate selected native facts and optionally current source receipts."""
    try:
        contract = _contract(Path(contract_path))
        expected = contract["nativeInputs"]
        root = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(
            expected["GameAssembly.dll"], expected["global-metadata.dat"],
            gameassembly=root.parent/"GameAssembly.dll" if root else None,
            metadata=root/"il2cpp_data/Metadata/global-metadata.dat" if root else None,
        )
        if gate.status != "validated":
            return {"status": gate.status, "validator": LABEL,
                    "failedCheck": "installed-native-inputs", "detail": gate.detail}
        unity = gate.gameassembly.parent/"UnityPlayer.dll"
        if not unity.is_file() or sha256_file(unity).upper() != expected["UnityPlayer.dll"].upper():
            return {"status": "mismatched", "validator": LABEL,
                    "failedCheck": "UnityPlayer.dll", "detail": "selected UnityPlayer.dll missing or different"}
        image = open_native_image(gate.gameassembly, gate.metadata)
        _validate_native(image, contract)
        checked = 0
        if export_root is not None:
            if ledger_path is None or summary_path is None:
                raise ValueError(f"{LABEL}.source:explicit-ledger-and-summary-required")
            checked = _validate_sources(contract, Path(export_root), Path(ledger_path), Path(summary_path))
        route = contract["route"]
        return {"status": "validated", "validator": LABEL, "evidenceBoundary": "exact",
                "route": {"family": route["family"], "tag": route["tag"],
                          "wrapperName": route["wrapperName"], "fields": route["fields"]},
                "sourceReceiptsChecked": checked, "nativeInputs": expected}
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as exc:
        failure = str(exc)
        check = (failure.split(".contract:", 1)[1] if ".contract:" in failure
                 else failure.split(".native:", 1)[1] if ".native:" in failure
                 else failure.split(".source:", 1)[1] if ".source:" in failure
                 else "contract-native-or-source")
        return {"status": "validation_failed", "validator": LABEL,
                "failedCheck": check, "detail": failure,
                "validationFailures": [{"gate": check, "actual": failure[:500]}]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    audit = validate_fac_change_building_native_contract(
        game_root=args.game_root, export_root=args.export_root,
        ledger_path=args.ledger, summary_path=args.summary,
    )
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
