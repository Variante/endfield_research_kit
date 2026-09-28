"""Validate selected native and source evidence for simple settlement actions."""

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
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import (
    generic_type_carrier, method_spec_record, method_spec_usage_index,
    unresolved_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-settlement-followon-native-contract.v1"
LABEL = "levelscriptSettlementFollowonNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_settlement_followon_native.json"
_NORMALIZED = {
    "bool": "bool", "int": "int32", "string": "string",
    "Beyond.GEnums.ScopeName": "int32",
    "Beyond.Gameplay.Actions.Param`1<bool>": "Param<bool>",
    "Beyond.Gameplay.Actions.Param`1<string>": "Param<string>",
}
_ELEMENT = {"Param<bool>": ("System.Boolean", "bool", 2),
            "Param<string>": ("System.String", "string", 14)}


def _contract(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_bytes())
    routes = data.get("routes", [])
    if (
        data.get("schema") != SCHEMA or data.get("status") != "exact-current-build"
        or data.get("evidenceBoundary") != "exact" or len(routes) != 3
        or len({row.get("tag") for row in routes}) != 3
        or not all(key in data.get("nativeInputs", {}) for key in
                   ("GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll"))
        or set(data.get("readerHelpers", {})) != {"bool", "int32", "string", "Param<bool>", "Param<string>"}
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    for route in routes:
        fields = route.get("fields", [])
        reads = route.get("orderedReads", [])
        receipts = route.get("sourceReceipts", [])
        if (
            route.get("family") != "ActionBase" or route.get("serializedMemberCount") != 9
            or route.get("inheritedMemberCount") != 8
            or len(fields) != 9 or len(route.get("nativeDeclaredTypes", [])) != 9
            or fields[8][1] not in _ELEMENT
            or [row.get("memberIndex") for row in reads] != list(range(9))
            or [[row.get("fieldName"), row.get("readKind")] for row in reads] != fields
            or [row[0] for row in route["nativeDeclaredTypes"]] != [row[0] for row in fields]
            or route.get("ownSetter", {}).get("memberIndex") != 8
            or route.get("nestedContext", {}).get("memberIndex") != 8
            or len(route.get("methods", [])) != 2 or len(route.get("codeWindows", [])) != 2
            or not receipts or any(len(row) != 5 for row in receipts)
            or len({(row[0], row[2]) for row in receipts}) != len(receipts)
            or not bytes.fromhex(route["memberCountInstruction"]["hex"]).endswith(b"\x09")
        ):
            raise ValueError(f"{LABEL}.contract:route-shape={route.get('tag')}")
    return data


def _call_target(image: Any, rva: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:call={rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_context(image: Any, context: dict[str, Any], kind: str) -> None:
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    spec_index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if spec_index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:param-spec-index")
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
        raise ValueError(f"{LABEL}.native:param-spec")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:param-arity")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"].upper() or raw[10] != context["typeKind"] != 0x15:
        raise ValueError(f"{LABEL}.native:param-argument")
    pointer = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(pointer, 32)
    base_raw = image.pe.bytes_at_va(struct.unpack_from("<Q", carrier_raw)[0], 16)
    carrier = generic_type_carrier(
        raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
        type_count=len(image.metadata.types), source=LABEL,
    )
    if (
        carrier != context["classCarrier"]
        or image.type_name(carrier["baseDefinitionIndex"]) != "Beyond.Gameplay.Actions.Param`1"
    ):
        raise ValueError(f"{LABEL}.native:param-carrier")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    if len(child.arguments) != 1 or child_row != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:param-instantiation")
    element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
    expected_name, runtime_name, expected_kind = _ELEMENT[kind]
    if (
        element.hex().upper() != context["elementRawHex"].upper()
        or element[10] != context["elementTypeKind"] != expected_kind
        or context["elementTypeName"] != expected_name
        or context["elementTypeDefinition"] is not None
        or protocol_runtime_type_name(image, child.arguments[0].type_pointer_va) != runtime_name
    ):
        raise ValueError(f"{LABEL}.native:param-element")


def protocol_runtime_type_name(image: Any, type_pointer_va: int) -> str:
    from scripts.game_data.il2cpp import protocol
    return protocol.runtime_type_name(image.pe, image.metadata, type_pointer_va)


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    base = image.pe.image_base
    wrappers = derive_from_image(image)
    switch = read_union_switch(
        image, "Beyond_Gameplay_Actions_ActionBaseForMemoryPack", wrappers=wrappers,
    )
    shape = contract["switch"]
    if (
        switch["entryCount"] != shape["entryCount"]
        or int(switch["tableVa"], 16) != base + shape["tableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-shape")
    table = image.pe.bytes_at_va(base + shape["tableRva"], shape["entryCount"] * 4)
    if hashlib.sha256(table).hexdigest().upper() != shape["tableSha256"].upper():
        raise ValueError(f"{LABEL}.native:switch-hash")
    body = BodyIndex(image)
    for route in contract["routes"]:
        tag = route["tag"]
        if not 0 <= tag < switch["entryCount"]:
            raise ValueError(f"{LABEL}.native:tag-range={tag}")
        branch = route["dispatcher"]
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
            raise ValueError(f"{LABEL}.native:dispatch-entry={tag}")
        if branch["branchWindow"]["startRva"] != branch["bodyRva"]:
            raise ValueError(f"{LABEL}.native:branch-range={tag}")
        image.check_windows([branch["branchWindow"]], label=LABEL)
        load_site = branch["typeLoadRva"]
        if not branch["bodyRva"] <= load_site <= branch["branchWindow"]["endRva"] - 7:
            raise ValueError(f"{LABEL}.native:type-load-range={tag}")
        load = image.pe.bytes_at_va(base + load_site, 7)
        if load[:3] != b"\x48\x8b\x15" or load.hex().upper() != branch["typeLoadHex"].upper():
            raise ValueError(f"{LABEL}.native:type-load={tag}")
        cell = base + load_site + 7 + struct.unpack_from("<i", load, 3)[0]
        usage = image.pe.bytes_at_va(cell, 8)
        index = unresolved_usage_index(
            usage, image.registration["typesCount"], tag=1, source=LABEL, offset=cell,
        )
        pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
        definition = struct.unpack_from("<Q", image.pe.bytes_at_va(pointer, 16))[0]
        if (
            cell - base != branch["usageCellRva"]
            or usage.hex().upper() != branch["usageRawHex"].upper()
            or index != route["registeredTypeIndex"]
            or definition != route["typeDefinition"]
            or image.type_name(definition) != route["wrapperName"]
        ):
            raise ValueError(f"{LABEL}.native:registered-wrapper={tag}")
        wrapper = wrappers[definition]
        if (
            wrapper.name != route["wrapperName"] or wrapper.wrapped_type != route["typeName"]
            or len(wrapper.members) != 9 or len(wrapper.inherited_members) != 8
            or len(wrapper.own_members) != 1
            or [[m.name.lstrip("_"), m.declared_type] for m in wrapper.members] != route["nativeDeclaredTypes"]
            or [[m.name.lstrip("_"), _NORMALIZED.get(m.declared_type)] for m in wrapper.members] != route["fields"]
            or any(m.kind != "enum" or m.underlying_kind != "scalar32" or m.width != 4
                   for m in wrapper.members if m.declared_type == "Beyond.GEnums.ScopeName")
        ):
            raise ValueError(f"{LABEL}.native:wrapper-fields={tag}")
        methods = [image.validate_method_row(row, label=LABEL) for row in route["methods"]]
        windows = route["codeWindows"]
        image.check_windows(windows, label=LABEL)
        image.check_instruction_windows([[
            route["memberCountInstruction"]["rva"], route["memberCountInstruction"]["hex"],
        ]], label=LABEL)
        if (
            route["methods"][0][1] != wrapper.name
            or not route["methods"][1][1].startswith(wrapper.name + "+")
        ):
            raise ValueError(f"{LABEL}.contract:method-owner={tag}")
        reader = image.method_pointer_va(image.metadata.methods[methods[0]])
        formatter = image.method_pointer_va(image.metadata.methods[methods[1]])
        if (
            windows[0]["startRva"] != reader-base
            or windows[0]["endRva"] != body.extents.get(reader, 0)-base
            or windows[1]["startRva"] != formatter-base
            or windows[1]["endRva"] != body.extents.get(formatter, 0)-base
            or body.chained_fragments.get(reader)
        ):
            raise ValueError(f"{LABEL}.native:complete-method-windows={tag}")
        count = route["memberCountInstruction"]["rva"]
        if not windows[0]["startRva"] < count < windows[0]["endRva"]:
            raise ValueError(f"{LABEL}.native:member-count-range={tag}")
        previous = count
        for read in route["orderedReads"]:
            site = read["sourceCallsiteRva"]
            if (
                not previous < site < windows[0]["endRva"]
                or _call_target(image, site, read["sourceCallHex"]) != read["sourceTargetRva"]
                or read["sourceTargetRva"] != contract["readerHelpers"][read["readKind"]]
            ):
                raise ValueError(f"{LABEL}.native:ordered-read={tag}:{read['memberIndex']}")
            previous = site
        setter = route["ownSetter"]
        member = wrapper.members[8]
        method = image.metadata.methods[setter["methodIndex"]]
        if (
            member.method_index != setter["methodIndex"]
            or member.declaring_wrapper != setter["declaringWrapper"]
            or image.type_name(method.declaring_type) != member.declaring_wrapper
            or image.metadata.string(method.name_index) != setter["setterName"]
            or image.method_pointer_va(method) != base + setter["targetRva"]
            or not route["orderedReads"][8]["sourceCallsiteRva"]
                < setter["callsiteRva"] < windows[0]["endRva"]
            or _call_target(image, setter["callsiteRva"], setter["callHex"]) != setter["targetRva"]
        ):
            raise ValueError(f"{LABEL}.native:setter={tag}")
        context = route["nestedContext"]
        if not route["orderedReads"][7]["sourceCallsiteRva"] < context["instructionRva"] < route["orderedReads"][8]["sourceCallsiteRva"]:
            raise ValueError(f"{LABEL}.native:param-context-order={tag}")
        _validate_context(image, context, route["fields"][8][1])


def _validate_sources(
    contract: dict[str, Any], export_root: Path, ledger_path: Path, summary_path: Path,
) -> dict[int, int]:
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

    checked = {}
    for route in contract["routes"]:
        tag = route["tag"]
        prefix = (bytes((tag, 9)) if tag < 0xFA
                  else b"\xfa" + tag.to_bytes(2, "little") + b"\x09")
        for path, digest, start, end, span_digest in route["sourceReceipts"]:
            data = (export_root / path).read_bytes()
            if (
                not 0 <= start < end <= len(data)
                or data[start:start+len(prefix)] != prefix
                or hashlib.sha256(data).hexdigest().upper() != digest.upper()
                or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
                or ledger.get(path, {}).get("length") != len(data)
                or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
            ):
                raise ValueError(f"{LABEL}.source:receipt={tag}:{path}")
            cursor = _Cursor(data, start+len(prefix))
            for name, kind in route["fields"]:
                cursor.value(kind, f"settlementFollowon{tag:04x}.{name}")
            if cursor.offset != end:
                raise ValueError(f"{LABEL}.source:end-offset={tag}:{path}")
        checked[tag] = len(route["sourceReceipts"])
    return checked


def validate_settlement_followon_native_contract(
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
        checked = {}
        if export_root is not None:
            if ledger_path is None or summary_path is None:
                raise ValueError(f"{LABEL}.source:explicit-ledger-and-summary-required")
            checked = _validate_sources(contract, Path(export_root), Path(ledger_path), Path(summary_path))
        return {"status": "validated", "validator": LABEL, "evidenceBoundary": "exact",
                "routeTags": [row["tag"] for row in contract["routes"]],
                "routes": [{"family": row["family"], "tag": row["tag"],
                            "wrapperName": row["wrapperName"], "fields": row["fields"]}
                           for row in contract["routes"]],
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
    audit = validate_settlement_followon_native_contract(
        game_root=args.game_root, export_root=args.export_root,
        ledger_path=args.ledger, summary_path=args.summary,
    )
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
