"""Authenticate the stored EntityEvent.OnBeingScanned ActionHeader layout.

This proves the selected native reader and source framing. It does not prove
when the event fires or which runtime system owns a scan.

The header has 18 inherited stored members and no own wrapper fields. After
the common event-header fields come `targetEntity` as `Param<EntityPtr>`,
`targetEntityList` as `Param<List<EntityPtr>>`, `targetEntityListOutput` as
`ParamOutput<EntityPtr>` and a stored `triggerTarget` enum. The validator
authenticates the selected switch and registered wrapper, complete reader
and formatter bodies, all 18 ordered reads and setters, and the nested
generic contexts; source receipts rejoin exact event-header cursors. The
shared ActionMap reader admits the route only while this validator passes.

Run as: python -m scripts.game_data.levelscript_entity_scanned_native
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
from scripts.game_data.codecs.levelscript import action_map
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import (
    generic_type_carrier, method_spec_record, method_spec_usage_index,
    unresolved_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-entity-scanned-native-contract.v1"
LABEL = "levelscriptEntityScannedNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_entity_scanned_native.json"


def _contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    route = contract.get("route", {})
    fields = route.get("fields", [])
    reads = contract.get("orderedReads", [])
    setters = contract.get("setters", [])
    contexts = contract.get("nestedContexts", [])
    count = route.get("serializedMemberCount")
    param_types = {
        "Param<bool>": ("Beyond.Gameplay.Actions.Param`1", "System.Boolean"),
        "Param<EntityPtr>": ("Beyond.Gameplay.Actions.Param`1", "Beyond.Gameplay.Core.EntityPtr"),
        "Param<List<EntityPtr>>": (
            "Beyond.Gameplay.Actions.Param`1",
            "System.Collections.Generic.List`1<Beyond.Gameplay.Core.EntityPtr>",
        ),
        "ParamOutput<EntityPtr>": (
            "Beyond.Gameplay.Actions.ParamOutput`1", "Beyond.Gameplay.Core.EntityPtr",
        ),
    }
    if contract.get("schema") != SCHEMA or contract.get("status") != "exact-current-build":
        raise ValueError(f"{LABEL}.contract:schema-or-status")
    if (
        contract.get("evidenceBoundary") != "exact"
        or route.get("family") != "ActionHeader"
        or not isinstance(route.get("tag"), int)
        or not isinstance(count, int) or not 0 < count < 256
        or route.get("inheritedMemberCount") != count
        or len(fields) != count or len(route.get("nativeDeclaredTypes", [])) != count
        or len(reads) != count or len(setters) != count
        or [row.get("memberIndex") for row in reads] != list(range(count))
        or [row.get("memberIndex") for row in setters] != list(range(count))
        or [[row.get("fieldName"), row.get("readKind")] for row in reads] != fields
        or [row[0] for row in route["nativeDeclaredTypes"]] != [row[0] for row in fields]
        or [row.get("memberIndex") for row in contexts] != [
            index for index, (_name, kind) in enumerate(fields)
            if kind.startswith("Param<") or kind.startswith("ParamOutput<")
        ]
        or any(
            param_types.get(fields[row["memberIndex"]][1])
            != (row.get("baseTypeName"), row.get("elementTypeName"))
            for row in contexts
        )
        or any(
            row.get("listBaseTypeName") != "System.Collections.Generic.List`1"
            or row.get("listElementTypeName") != "Beyond.Gameplay.Core.EntityPtr"
            for row in contexts if fields[row["memberIndex"]][1] == "Param<List<EntityPtr>>"
        )
        or len(contract.get("methods", [])) != 2
        or len(contract.get("codeWindows", [])) != 2
        or len(contract.get("sourceReceipts", [])) < 1
        or any(len(row) != 5 for row in contract["sourceReceipts"])
    ):
        raise ValueError(f"{LABEL}.contract:route-shape")
    helpers = contract.get("readerHelpers", {})
    if set(helpers) != {kind for _name, kind in fields}:
        raise ValueError(f"{LABEL}.contract:reader-helpers")
    return contract


def _call_target(image: Any, rva: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:call={rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_context(image: Any, context: dict[str, Any]) -> None:
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:context-method-spec-index={context['memberIndex']}")
    address = int(image.registration["methodSpecs"], 16) + index * 12
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
        raise ValueError(f"{LABEL}.native:context-method-spec={context['memberIndex']}")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:context-method-arity={context['memberIndex']}")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"] or raw[10] != context["typeKind"] != 0x15:
        raise ValueError(f"{LABEL}.native:context-argument={context['memberIndex']}")
    carrier_pointer = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(carrier_pointer, 32)
    base_pointer = struct.unpack_from("<Q", carrier_raw)[0]
    base_raw = image.pe.bytes_at_va(base_pointer, 16)
    carrier = generic_type_carrier(
        raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
        type_count=len(image.metadata.types), source=LABEL,
    )
    if (
        carrier != context["classCarrier"]
        or image.type_name(carrier["baseDefinitionIndex"]) != context["baseTypeName"]
    ):
        raise ValueError(f"{LABEL}.native:context-base={context['memberIndex']}")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    if len(child.arguments) != 1 or child_row != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:context-instantiation={context['memberIndex']}")
    element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
    if (
        element.hex().upper() != context["elementRawHex"]
        or element[10] != context["elementTypeKind"]
    ):
        raise ValueError(f"{LABEL}.native:context-element={context['memberIndex']}")
    if context["elementTypeName"] == "System.Boolean":
        if element[10] != 2 or context["elementTypeDefinition"] is not None:
            raise ValueError(f"{LABEL}.native:context-bool")
    elif context["elementTypeName"] == "Beyond.Gameplay.Core.EntityPtr":
        definition = struct.unpack_from("<Q", element)[0]
        if (
            element[10] != 0x11 or definition != context["elementTypeDefinition"]
            or image.type_name(definition) != context["elementTypeName"]
        ):
            raise ValueError(f"{LABEL}.native:context-entityptr")
    else:
        if element[10] != 0x15 or context["elementTypeDefinition"] is not None:
            raise ValueError(f"{LABEL}.native:context-list-kind")
        list_pointer = struct.unpack_from("<Q", element)[0]
        list_raw = image.pe.bytes_at_va(list_pointer, 32)
        list_base_pointer = struct.unpack_from("<Q", list_raw)[0]
        list_base_raw = image.pe.bytes_at_va(list_base_pointer, 16)
        list_carrier = generic_type_carrier(
            element, list_raw, list_base_raw,
            type_pointer=child.arguments[0].type_pointer_va,
            type_count=len(image.metadata.types), source=LABEL,
        )
        if (
            list_carrier != context["listCarrier"]
            or image.type_name(list_carrier["baseDefinitionIndex"])
            != context["listBaseTypeName"]
        ):
            raise ValueError(f"{LABEL}.native:context-list-carrier")
        nested = image.instantiations.resolve_pointer(list_carrier["classInstantiationPointerVa"])
        nested_row = nested.as_dict()
        nested_row["arguments"] = list(nested_row["arguments"])
        if nested_row != context["listInstantiation"] or len(nested.arguments) != 1:
            raise ValueError(f"{LABEL}.native:context-list-instantiation")
        nested_element = bytes.fromhex(nested.arguments[0].raw_type_record_hex)
        definition = struct.unpack_from("<Q", nested_element)[0]
        if (
            nested_element[10] != 0x11
            or image.type_name(definition) != context["listElementTypeName"]
        ):
            raise ValueError(f"{LABEL}.native:context-list-entityptr")


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    route = contract["route"]
    dispatch = contract["dispatcher"]
    tag = route["tag"]
    base = image.pe.image_base
    wrappers = derive_from_image(image)
    switch = read_union_switch(image, "Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", wrappers=wrappers)
    if (
        not 0 <= tag < switch["entryCount"]
        or switch["entryCount"] != dispatch["switchEntryCount"]
        or int(switch["tableVa"], 16) != base + dispatch["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-shape")
    table = image.pe.bytes_at_va(base + dispatch["switchTableRva"], switch["entryCount"] * 4)
    if hashlib.sha256(table).hexdigest().upper() != dispatch["switchTableSha256"].upper():
        raise ValueError(f"{LABEL}.native:switch-hash")
    entry = switch["entries"][tag]
    target = struct.unpack_from("<I", table, tag * 4)[0]
    if (
        target != dispatch["switchTargetRva"] == dispatch["bodyRva"]
        or int(entry["targetVa"], 16) != base + target
        or int(entry["bodyVa"], 16) != base + target
        or entry["wrapperName"] != route["wrapperName"]
        or entry["registeredTypeIndex"] != route["registeredTypeIndex"]
        or entry["typeDefinition"] != route["typeDefinition"]
    ):
        raise ValueError(f"{LABEL}.native:direct-branch")
    branch = dispatch["branchWindow"]
    if branch["startRva"] != target or branch["endRva"] <= branch["startRva"]:
        raise ValueError(f"{LABEL}.contract:branch-window")
    image.check_windows([branch], label=LABEL)
    load_rva = dispatch["typeLoadRva"]
    load = image.pe.bytes_at_va(base + load_rva, 7)
    if (
        not branch["startRva"] <= load_rva < branch["endRva"] - 7
        or load[:3] != b"\x48\x8b\x15"
        or load.hex().upper() != dispatch["typeLoadHex"].upper()
    ):
        raise ValueError(f"{LABEL}.native:type-load")
    cell = base + load_rva + 7 + struct.unpack_from("<i", load, 3)[0]
    usage = image.pe.bytes_at_va(cell, 8)
    index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1, source=LABEL, offset=cell,
    )
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    definition = struct.unpack_from("<Q", image.pe.bytes_at_va(pointer, 16))[0]
    if (
        cell-base != dispatch["usageCellRva"]
        or usage.hex().upper() != dispatch["usageRawHex"].upper()
        or index != route["registeredTypeIndex"]
        or definition != route["typeDefinition"]
        or image.type_name(definition) != route["wrapperName"]
    ):
        raise ValueError(f"{LABEL}.native:registered-wrapper")
    wrapper = wrappers[definition]
    if (
        wrapper.name != route["wrapperName"]
        or wrapper.wrapped_type != route["typeName"]
        or len(wrapper.members) != route["serializedMemberCount"]
        or len(wrapper.inherited_members) != route["inheritedMemberCount"]
        or wrapper.own_members
        or [[member.name.lstrip("_"), member.declared_type]
            for member in wrapper.members] != route["nativeDeclaredTypes"]
    ):
        raise ValueError(f"{LABEL}.native:wrapper-fields")

    method_indices = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    windows = contract["codeWindows"]
    image.check_windows(windows, label=LABEL)
    image.check_instruction_windows([
        [contract["memberCountInstruction"]["rva"], contract["memberCountInstruction"]["hex"]]
    ], label=LABEL)
    if bytes.fromhex(contract["memberCountInstruction"]["hex"])[-1] != route["serializedMemberCount"]:
        raise ValueError(f"{LABEL}.contract:member-count")
    extents = image.mapper.pdata_function_extents(image.pe)
    for method_index, window in zip(method_indices, windows):
        pointer = image.method_pointer_va(image.metadata.methods[method_index])
        if window["startRva"] != pointer-base or window["endRva"] != extents.get(pointer, 0)-base:
            raise ValueError(f"{LABEL}.native:method-extent")
    source_pointer = base + windows[0]["startRva"]
    if BodyIndex(image).chained_fragments.get(source_pointer):
        raise ValueError(f"{LABEL}.native:unrecorded-source-fragments")
    if (
        contract["methods"][0][1] != wrapper.name
        or not contract["methods"][1][1].startswith(wrapper.name + "+")
    ):
        raise ValueError(f"{LABEL}.contract:methods")
    previous = contract["memberCountInstruction"]["rva"]
    source_window = windows[0]
    for read, setter, member in zip(contract["orderedReads"], contract["setters"], wrapper.members):
        member_index = read["memberIndex"]
        site = read["sourceCallsiteRva"]
        if (
            not previous < site < source_window["endRva"]
            or _call_target(image, site, read["sourceCallHex"])
            != read["sourceTargetRva"]
            or read["sourceTargetRva"] != contract["readerHelpers"][read["readKind"]]
        ):
            raise ValueError(f"{LABEL}.native:ordered-read={member_index}")
        method_index = setter["methodIndex"]
        method = image.metadata.methods[method_index]
        if (
            member.method_index != method_index
            or member.declaring_wrapper != setter["declaringWrapper"]
            or image.type_name(method.declaring_type) != member.declaring_wrapper
            or image.metadata.string(method.name_index) != setter["setterName"]
            or not site < setter["callsiteRva"] < source_window["endRva"]
            or _call_target(image, setter["callsiteRva"], setter["callHex"])
            != setter["targetRva"]
            or image.method_pointer_va(method) != base + setter["targetRva"]
        ):
            raise ValueError(f"{LABEL}.native:setter={member_index}")
        previous = setter["callsiteRva"]
    for context in contract["nestedContexts"]:
        member_index = context["memberIndex"]
        if not (
            contract["orderedReads"][member_index-1]["sourceCallsiteRva"]
            < context["instructionRva"]
            < contract["orderedReads"][member_index]["sourceCallsiteRva"]
        ):
            raise ValueError(f"{LABEL}.native:context-order={member_index}")
        _validate_context(image, context)


def _validate_sources(contract: dict[str, Any], export_root: Path, ledger_path: Path) -> int:
    ledger = {}
    with gzip.open(ledger_path, "rt", encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData":
                ledger[row["exportRelativePath"]] = row
    route = contract["route"]
    checked = 0
    for relative_path, digest, start, end, span_digest in contract["sourceReceipts"]:
        data = (export_root / relative_path).read_bytes()
        if (
            not 0 <= start < end <= len(data)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or ledger.get(relative_path, {}).get("logicalSha256", "").upper() != digest.upper()
            or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
        ):
            raise ValueError(f"{LABEL}.source:receipt={relative_path}")
        cursor = action_map._Cursor(data, start)
        tag = cursor.byte("entityScanned.tag")
        members = cursor.byte("entityScanned.memberCount")
        if tag != route["tag"] or members != route["serializedMemberCount"]:
            raise ValueError(f"{LABEL}.source:union-header={relative_path}")
        for name, kind in route["fields"]:
            cursor.value(kind, "entityScanned." + name)
        if cursor.offset != end:
            raise ValueError(f"{LABEL}.source:end-offset={relative_path}")
        checked += 1
    return checked


def validate_entity_scanned_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Validate selected native facts and optionally seven source receipts."""
    try:
        contract = _contract(Path(contract_path))
        expected = contract["nativeInputs"]
        root = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(
            expected["GameAssembly.dll"], expected["global-metadata.dat"],
            gameassembly=root.parent / "GameAssembly.dll" if root else None,
            metadata=root / "il2cpp_data/Metadata/global-metadata.dat" if root else None,
        )
        if gate.status != "validated":
            return {"status": gate.status, "validator": LABEL,
                    "failedCheck": "installed-native-inputs", "detail": gate.detail}
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        if not unity.is_file() or sha256_file(unity).upper() != expected["UnityPlayer.dll"].upper():
            return {"status": "mismatched", "validator": LABEL,
                    "failedCheck": "UnityPlayer.dll", "detail": "selected UnityPlayer.dll missing or different"}
        image = open_native_image(gate.gameassembly, gate.metadata)
        _validate_native(image, contract)
        checked = 0
        if export_root is not None:
            if ledger_path is None:
                raise ValueError(f"{LABEL}.source:explicit-ledger-required")
            checked = _validate_sources(contract, Path(export_root), Path(ledger_path))
        route = contract["route"]
        return {"status": "validated", "validator": LABEL, "evidenceBoundary": "exact",
                "route": {"family": route["family"], "tag": route["tag"],
                          "wrapperName": route["wrapperName"], "fields": route["fields"]},
                "sourceReceiptsChecked": checked, "nativeInputs": expected}
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as exc:
        return {"status": "validation_failed", "validator": LABEL,
                "failedCheck": str(exc).split(":", 1)[-1][:160], "detail": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--ledger", type=Path)
    args = parser.parse_args()
    audit = validate_entity_scanned_native_contract(export_root=args.export_root, ledger_path=args.ledger)
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
