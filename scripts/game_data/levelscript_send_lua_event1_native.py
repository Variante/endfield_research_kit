"""Authenticate SendLuaEvent1's selected stored ActionBase layout.

The native contract proves the generated outer reader and nested type. Current
source receipts prove the seven-member inner record, not a live Lua event.

The generated outer reader makes eight ordinary setter calls for the
inherited action fields, then `ReadValue<SendLuaEvent1>` and an instance
assignment; it never calls the wrapper's declared `manualValue` setter. The
nested wire value has seven members: ID, UID, two boolean and one integer
position that keep neutral names, the event-name `Param<string>`, and a
string holding a JSON parameter descriptor. The native switch, wrapper,
complete reader and formatter, and nested type context authenticate the
outer route; the inner seven-member shape rests on ledger-joined source
cursors and whole-file framing, not on a native read of those members.
`codecs.levelscript.send_lua_event` reads the inner value and records why
the derived declaration cannot describe it.

Run as: python -m scripts.game_data.levelscript_send_lua_event1_native
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
    method_spec_record, method_spec_usage_index, unresolved_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-send-lua-event1-native-contract.v1"
LABEL = "levelscriptSendLuaEvent1Native"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_send_lua_event1_native.json"


def _contract(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_bytes())
    route = data.get("route", {})
    fields = route.get("fields", [])
    reads = data.get("orderedReads", [])
    setters = data.get("setters", [])
    contexts = data.get("nestedContexts", [])
    assignment = data.get("nestedAssignment", {})
    nested = data.get("nestedValue", {})
    enums = data.get("enumTypes", [])
    receipts = data.get("sourceReceipts", [])
    if (
        data.get("schema") != SCHEMA
        or data.get("status") != "exact-current-build"
        or data.get("evidenceBoundary") != "exact"
        or route.get("family") != "ActionBase"
        or route.get("tag") != 0x3C1
        or route.get("typeName") != "Beyond.Gameplay.Actions.SendLuaEvent1"
        or route.get("serializedMemberCount") != 9
        or route.get("inheritedMemberCount") != 8
        or len(fields) != 9 or len(route.get("nativeDeclaredTypes", [])) != 9
        or fields[8] != ["manualValue", "SendLuaEvent1"]
        or [row[0] for row in route["nativeDeclaredTypes"]] != [row[0] for row in fields]
        or len(reads) != 9 or len(setters) != 8
        or [row.get("memberIndex") for row in reads] != list(range(9))
        or [row.get("memberIndex") for row in setters] != list(range(8))
        or [[row.get("fieldName"), row.get("readKind")] for row in reads] != fields
        or set(data.get("readerHelpers", {})) != {kind for _, kind in fields}
        or [row.get("memberIndex") for row in contexts] != [8]
        or [row.get("typeName") for row in contexts] != ["Beyond.Gameplay.Actions.SendLuaEvent1"]
        or assignment.get("memberIndex") != 8
        or assignment.get("declaredSetterName") != "set___manualValue__"
        or assignment.get("assignmentName") != "set___instance"
        or nested != {"memberCount": 7, "jsonParamCount": 1,
                      "fieldKinds": ["int32", "string", "bool", "int32", "bool",
                                     "Param<string>", "string"]}
        or enums != []
        or len(data.get("methods", [])) != 2 or len(data.get("codeWindows", [])) != 2
        or bytes.fromhex(data["memberCountInstruction"]["hex"])[-1] != 9
        or not receipts or any(len(row) != 7 for row in receipts)
        or len({(row[0], row[2]) for row in receipts}) != len(receipts)
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return data


def _call_target(image: Any, rva: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base+rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:call={rva:#x}")
    return rva+5+struct.unpack_from("<i", raw, 1)[0]


def _validate_context(image: Any, context: dict[str, Any]) -> None:
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:nested-spec-index={context['memberIndex']}")
    address = int(image.registration["methodSpecs"], 16)+index*12
    spec = method_spec_record(
        image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source=LABEL, offset=address,
    )
    method = image.metadata.methods[spec[0]]
    instance = image.instantiations.resolve(spec[2])
    if (
        list(spec) != context["methodSpec"] or len(instance.arguments) != 1
        or image.type_name(method.declaring_type) != "MemoryPack.MemoryPackReader"
        or image.metadata.string(method.name_index) != "ReadValue"
    ):
        raise ValueError(f"{LABEL}.native:nested-readvalue={context['memberIndex']}")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    definition = struct.unpack_from("<Q", raw)[0]
    actual_name = protocol.runtime_type_name(image.pe, image.metadata, argument.type_pointer_va)
    if (
        actual_name != context["typeName"] != "Beyond.Gameplay.Actions.SendLuaEvent1"
        or raw.hex().upper() != context["argumentRawHex"].upper()
        or raw[10] != context["typeKind"] != 0x12
        or definition != context["typeDefinition"]
        or image.type_name(definition) != actual_name
    ):
        raise ValueError(f"{LABEL}.native:nested-class-type={context['memberIndex']}")


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    base = image.pe.image_base
    route, dispatch = contract["route"], contract["dispatcher"]
    wrappers = derive_from_image(image)
    switch = read_union_switch(
        image, "Beyond_Gameplay_Actions_ActionBaseForMemoryPack", wrappers=wrappers,
    )
    if (
        switch["entryCount"] != dispatch["switchEntryCount"]
        or int(switch["tableVa"], 16) != base+dispatch["switchTableRva"]
        or not 0 <= route["tag"] < switch["entryCount"]
    ):
        raise ValueError(f"{LABEL}.native:switch-shape")
    table = image.pe.bytes_at_va(base+dispatch["switchTableRva"], switch["entryCount"]*4)
    if hashlib.sha256(table).hexdigest().upper() != dispatch["switchTableSha256"].upper():
        raise ValueError(f"{LABEL}.native:switch-hash")
    target = struct.unpack_from("<I", table, route["tag"]*4)[0]
    jump = image.pe.bytes_at_va(base+target, 5)
    entry = switch["entries"][route["tag"]]
    if (
        target != dispatch["switchTargetRva"] or jump[0] != 0xE9
        or jump.hex().upper() != dispatch["switchEntryHex"].upper()
        or target+5+struct.unpack_from("<i", jump, 1)[0] != dispatch["bodyRva"]
        or int(entry["targetVa"], 16) != base+target
        or int(entry["bodyVa"], 16) != base+dispatch["bodyRva"]
        or entry["wrapperName"] != route["wrapperName"]
        or entry["typeDefinition"] != route["typeDefinition"]
        or entry["registeredTypeIndex"] != route["registeredTypeIndex"]
    ):
        raise ValueError(f"{LABEL}.native:switch-entry")
    branch = dispatch["branchWindow"]
    if branch["startRva"] != dispatch["bodyRva"]:
        raise ValueError(f"{LABEL}.contract:branch-window")
    image.check_windows([branch], label=LABEL)
    load_rva = dispatch["typeLoadRva"]
    load = image.pe.bytes_at_va(base+load_rva, 7)
    if (
        not branch["startRva"] <= load_rva < branch["endRva"]-7
        or load[:3] != b"\x48\x8b\x15"
        or load.hex().upper() != dispatch["typeLoadHex"].upper()
    ):
        raise ValueError(f"{LABEL}.native:type-load")
    cell = base+load_rva+7+struct.unpack_from("<i", load, 3)[0]
    usage = image.pe.bytes_at_va(cell, 8)
    index = unresolved_usage_index(usage, image.registration["typesCount"], tag=1,
                                   source=LABEL, offset=cell)
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16)+index*8)
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
    native_types = [[member.name.lstrip("_"), member.declared_type] for member in wrapper.members]
    normalized = {
        "bool": "bool", "int": "int32", "string": "string",
        "Beyond.GEnums.ScopeName": "int32",
        "Beyond.Gameplay.Actions.SendLuaEvent1": "SendLuaEvent1",
    }
    if (
        wrapper.name != route["wrapperName"] or wrapper.wrapped_type != route["typeName"]
        or len(wrapper.members) != 9 or len(wrapper.inherited_members) != 8
        or len(wrapper.own_members) != 1 or native_types != route["nativeDeclaredTypes"]
        or [[name, normalized.get(kind)] for name, kind in native_types] != route["fields"]
    ):
        raise ValueError(f"{LABEL}.native:wrapper-fields")
    method_indices = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    windows = contract["codeWindows"]
    image.check_windows(windows, label=LABEL)
    image.check_instruction_windows([
        [contract["memberCountInstruction"]["rva"], contract["memberCountInstruction"]["hex"]]
    ], label=LABEL)
    if (
        contract["methods"][0][1] != wrapper.name
        or not contract["methods"][1][1].startswith(wrapper.name+"+")
    ):
        raise ValueError(f"{LABEL}.contract:method-owner")
    reader_ptr = image.method_pointer_va(image.metadata.methods[method_indices[0]])
    formatter_ptr = image.method_pointer_va(image.metadata.methods[method_indices[1]])
    body = BodyIndex(image)
    if (
        windows[0]["startRva"] != reader_ptr-base
        or windows[0]["endRva"] != body.extents.get(reader_ptr, 0)-base
        or windows[-1]["startRva"] != formatter_ptr-base
        or windows[-1]["endRva"] != body.extents.get(formatter_ptr, 0)-base
        or [(row["startRva"], row["endRva"]) for row in windows[1:-1]]
        != [(pointer-base, pointer+length-base)
            for pointer, length in body.chained_fragments.get(reader_ptr, [])]
    ):
        raise ValueError(f"{LABEL}.native:complete-method-windows")
    source_ranges = [(row["startRva"], row["endRva"]) for row in windows[:-1]]
    count = contract["memberCountInstruction"]
    if not any(start <= count["rva"] < end for start, end in source_ranges):
        raise ValueError(f"{LABEL}.native:member-count-range")
    previous = count["rva"]
    for read, setter, member in zip(contract["orderedReads"][:8], contract["setters"], wrapper.members[:8]):
        i, site = read["memberIndex"], read["sourceCallsiteRva"]
        if (
            not previous < site
            or not any(start <= site < end for start, end in source_ranges)
            or _call_target(image, site, read["sourceCallHex"]) != read["sourceTargetRva"]
            or read["sourceTargetRva"] != contract["readerHelpers"][read["readKind"]]
        ):
            raise ValueError(f"{LABEL}.native:ordered-read={i}")
        method_index = setter["methodIndex"]
        method = image.metadata.methods[method_index]
        callsite = setter["callsiteRva"]
        if (
            member.method_index != method_index
            or member.declaring_wrapper != setter["declaringWrapper"]
            or image.type_name(method.declaring_type) != member.declaring_wrapper
            or image.metadata.string(method.name_index) != setter["setterName"]
            or not site < callsite < contract["orderedReads"][i+1]["sourceCallsiteRva"]
            or _call_target(image, callsite, setter["callHex"]) != setter["targetRva"]
            or image.method_pointer_va(method) != base+setter["targetRva"]
        ):
            raise ValueError(f"{LABEL}.native:setter={i}")
        previous = callsite
    last = contract["orderedReads"][8]
    if (
        not previous < last["sourceCallsiteRva"]
        or not any(start <= last["sourceCallsiteRva"] < end for start, end in source_ranges)
        or _call_target(image, last["sourceCallsiteRva"], last["sourceCallHex"])
        != last["sourceTargetRva"]
        or last["sourceTargetRva"] != contract["readerHelpers"]["SendLuaEvent1"]
    ):
        raise ValueError(f"{LABEL}.native:nested-read")
    assignment = contract["nestedAssignment"]
    declared_setter = image.metadata.methods[assignment["declaredSetterMethodIndex"]]
    actual_setter = image.metadata.methods[assignment["assignmentMethodIndex"]]
    if (
        wrapper.members[8].method_index != assignment["declaredSetterMethodIndex"]
        or image.type_name(declared_setter.declaring_type) != wrapper.name
        or image.metadata.string(declared_setter.name_index) != assignment["declaredSetterName"]
        or image.type_name(actual_setter.declaring_type) != assignment["declaringWrapper"] != wrapper.name
        or image.metadata.string(actual_setter.name_index) != assignment["assignmentName"]
        or not last["sourceCallsiteRva"] < assignment["callsiteRva"] < windows[0]["endRva"]
        or _call_target(image, assignment["callsiteRva"], assignment["callHex"])
        != assignment["targetRva"]
        or image.method_pointer_va(actual_setter) != base+assignment["targetRva"]
    ):
        raise ValueError(f"{LABEL}.native:nested-assignment")
    for context in contract["nestedContexts"]:
        i = context["memberIndex"]
        if not contract["orderedReads"][i-1]["sourceCallsiteRva"] < context["instructionRva"] < contract["orderedReads"][i]["sourceCallsiteRva"]:
            raise ValueError(f"{LABEL}.native:context-order={i}")
        _validate_context(image, context)


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
    from scripts.game_data.codecs.levelscript import send_lua_event

    for path, digest, start, end, span_digest, id_offset, script_id in contract["sourceReceipts"]:
        data = (export_root/path).read_bytes()
        if (
            not 0 <= start < end <= len(data)
            or not 0 <= id_offset <= len(data)-8
            or data[start:start+4] != bytes((0xFA, 0xC1, 0x03, 9))
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
            or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
            or ledger.get(path, {}).get("length") != len(data)
            or int.from_bytes(data[id_offset:id_offset+8], "little") != script_id
            or not Path(path).stem.isdecimal() or int(Path(path).stem) != script_id
        ):
            raise ValueError(f"{LABEL}.source:receipt={path}")
        cursor = _Cursor(data, start)
        if (cursor.byte("sendLuaEvent1.wideMarker") != 0xFA
                or cursor.byte("sendLuaEvent1.tagLo") != 0xC1
                or cursor.byte("sendLuaEvent1.tagHi") != 0x03
                or cursor.byte("sendLuaEvent1.memberCount") != 9):
            raise ValueError(f"{LABEL}.source:union-header={path}")
        for name, kind in contract["route"]["fields"][:8]:
            cursor.value(kind, "sendLuaEvent1."+name)
        if (
            contract["nestedValue"]["memberCount"]
            != send_lua_event.FIXED_MEMBER_COUNT+contract["nestedValue"]["jsonParamCount"]
        ):
            raise ValueError(f"{LABEL}.source:nested-shape-contract")
        _nested, cursor.offset = send_lua_event.decode_nested_send_lua_event(
            data, cursor.offset, "sendLuaEvent1.manualValue",
            contract["nestedValue"]["jsonParamCount"],
        )
        if cursor.offset != end:
            raise ValueError(f"{LABEL}.source:end-offset={path}")
    return len(contract["sourceReceipts"])


def validate_send_lua_event1_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Validate selected native route and optionally joined source receipts."""
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
    audit = validate_send_lua_event1_native_contract(
        game_root=args.game_root, export_root=args.export_root,
        ledger_path=args.ledger, summary_path=args.summary,
    )
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
