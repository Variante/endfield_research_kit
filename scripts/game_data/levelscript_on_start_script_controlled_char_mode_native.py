"""Authenticate the stored OnStartScriptControlledCharMode ActionHeader route.

This proves the selected native reader, typed parameter contexts and current
source cursors. It does not prove event execution or output values.

The reached header stores an entity output path and an authored scripted ID
filter. Its target script is null in the selected source.

Run as: python -m scripts.game_data.levelscript_on_start_script_controlled_char_mode_native
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
from scripts.game_data.memorypack.wrapper_members import derive_from_image, enum_widths_from_image


SCHEMA = "endfield.levelscript-on-start-script-controlled-char-mode-native-contract.v1"
LABEL = "levelscriptOnStartScriptControlledCharModeNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_on_start_script_controlled_char_mode_native.json"
_PARAM_ELEMENTS = {
    "Param<bool>": ("bool", "bool", 0x02, "Beyond.Gameplay.Actions.Param`1"),
    "Param<LevelScriptPtr>": (
        "Beyond.Gameplay.Core.LevelScriptPtr", "Beyond.Gameplay.Core.LevelScriptPtr",
        0x11, "Beyond.Gameplay.Actions.Param`1"),
    "ParamOutput<EntityPtr>": (
        "Beyond.Gameplay.Core.EntityPtr", "Beyond.Gameplay.Core.EntityPtr",
        0x11, "Beyond.Gameplay.Actions.ParamOutput`1"),
    "Param<string>": ("string", "string", 0x0E, "Beyond.Gameplay.Actions.Param`1"),
}


def _contract(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_bytes())
    route = data.get("route", {})
    fields = route.get("fields", [])
    reads = data.get("orderedReads", [])
    setters = data.get("setters", [])
    contexts = data.get("nestedContexts", [])
    count = route.get("serializedMemberCount")
    inherited = route.get("inheritedMemberCount")
    own = route.get("ownMemberCount")
    parameter_indexes = [index for index, (_name, kind) in enumerate(fields)
                         if kind in _PARAM_ELEMENTS]
    if (
        data.get("schema") != SCHEMA
        or data.get("status") != "exact-current-build"
        or data.get("evidenceBoundary") != "exact"
        or route.get("family") != "ActionHeader"
        or not 0 <= route.get("tag", -1) < 0xFA
        or not isinstance(route.get("tag"), int)
        or not isinstance(count, int) or not isinstance(inherited, int)
        or not isinstance(own, int)
        or count <= 0 or not 0 <= inherited <= count or own != count - inherited
        or len(fields) != count or len(route.get("nativeDeclaredTypes", [])) != count
        or [row.get("memberIndex") for row in reads] != list(range(count))
        or [[row.get("fieldName"), row.get("readKind")] for row in reads] != fields
        or [row[0] for row in route["nativeDeclaredTypes"]] != [row[0] for row in fields]
        or set(data.get("readerHelpers", {})) != {kind for _, kind in fields}
        or [row.get("memberIndex") for row in setters] != list(range(count))
        or [row.get("memberIndex") for row in contexts] != parameter_indexes
        or [(row.get("elementTypeName"), row.get("elementTypeKind")) for row in contexts]
        != [(_PARAM_ELEMENTS[fields[index][1]][0], _PARAM_ELEMENTS[fields[index][1]][2])
            for index in parameter_indexes]
        or [row.get("baseTypeName") for row in contexts]
        != [_PARAM_ELEMENTS[fields[index][1]][3] for index in parameter_indexes]
        or [row.get("readerMethodName") for row in contexts] != ["ReadValue"] * len(contexts)
        or set(data.get("enumWidths", {})) != {
            "Beyond.Gameplay.Actions.FilterLevel", "Beyond.Gameplay.Actions.FilterMask",
            "Beyond.Gameplay.Actions.TriggerActiveDuring",
            "Beyond.Gameplay.Actions.ScriptEventHeader+TriggerTarget"}
        or any(width != 4 for width in data["enumWidths"].values())
        or len(data.get("methods", [])) != 2
        or len(data.get("codeWindows", [])) != 2
        or not data.get("sourceReceipts")
        or any(len(row) != 5 for row in data["sourceReceipts"])
        or len({(row[0], row[2]) for row in data["sourceReceipts"]}) != len(data["sourceReceipts"])
        or bytes.fromhex(data["memberCountInstruction"]["hex"])[-1] != count
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
        or image.type_name(carrier["baseDefinitionIndex"]) != context["baseTypeName"]
    ):
        raise ValueError(f"{LABEL}.native:param-carrier={member}")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    if len(child.arguments) != 1 or child_row != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:param-instantiation={member}")
    element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
    expected_name, runtime_name, expected_kind, _base_name = _PARAM_ELEMENTS[kind]
    definition = struct.unpack_from("<Q", element)[0] if expected_kind == 0x11 else None
    if (
        element.hex().upper() != context["elementRawHex"].upper()
        or element[10] != context["elementTypeKind"] != expected_kind
        or context["elementTypeName"] != expected_name
        or protocol.runtime_type_name(image.pe, image.metadata, child.arguments[0].type_pointer_va) != runtime_name
        or definition != context["elementTypeDefinition"]
        or (definition is not None and image.type_name(definition) != expected_name)
    ):
        raise ValueError(f"{LABEL}.native:param-element={member}")


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    route = contract["route"]
    branch = contract["dispatcher"]
    base = image.pe.image_base
    wrappers = derive_from_image(image)
    switch = read_union_switch(
        image, "Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", wrappers=wrappers,
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
    if (
        target != branch["switchTargetRva"] or target != branch["bodyRva"]
        or int(entry["targetVa"], 16) != base + target
        or int(entry["bodyVa"], 16) != base + branch["bodyRva"]
        or int(entry["usageCellVa"], 16) != base + branch["usageCellRva"]
        or entry["wrapperName"] != route["wrapperName"]
        or entry["typeDefinition"] != route["typeDefinition"]
        or entry["registeredTypeIndex"] != route["registeredTypeIndex"]
    ):
        raise ValueError(f"{LABEL}.native:dispatch-entry")
    usage_cell = base + branch["usageCellRva"]
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
        "Beyond.Gameplay.Actions.FilterLevel": "int32",
        "Beyond.Gameplay.Actions.FilterMask": "int32",
        "Beyond.Gameplay.Actions.TriggerActiveDuring": "int32",
        "Beyond.Gameplay.Actions.Param`1<bool>": "Param<bool>",
        "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.LevelScriptPtr>": "Param<LevelScriptPtr>",
        "Beyond.Gameplay.Actions.ScriptEventHeader+TriggerTarget": "int32",
        "Beyond.Gameplay.Actions.ParamOutput`1<Beyond.Gameplay.Core.EntityPtr>": "ParamOutput<EntityPtr>",
        "Beyond.Gameplay.Actions.Param`1<string>": "Param<string>",
    }
    if (
        wrapper.name != route["wrapperName"]
        or wrapper.wrapped_type != route["typeName"]
        or len(wrapper.members) != route["serializedMemberCount"]
        or len(wrapper.inherited_members) != route["inheritedMemberCount"]
        or len(wrapper.own_members) != route["ownMemberCount"]
        or [[member.name.lstrip("_"), member.declared_type] for member in wrapper.members] != route["nativeDeclaredTypes"]
        or [[member.name.lstrip("_"), normalized.get(member.declared_type)] for member in wrapper.members] != route["fields"]
        or any(member.kind != "enum" or member.underlying_kind != "scalar32" or member.width != 4
               for member in wrapper.members if member.declared_type in (
                   "Beyond.GEnums.ScopeName", "Beyond.Gameplay.Actions.FilterLevel",
                   "Beyond.Gameplay.Actions.FilterMask", "Beyond.Gameplay.Actions.TriggerActiveDuring",
                   "Beyond.Gameplay.Actions.ScriptEventHeader+TriggerTarget"))
    ):
        raise ValueError(f"{LABEL}.native:wrapper-fields")
    widths = enum_widths_from_image(image)
    if any(widths.get(name) != width for name, width in contract["enumWidths"].items()):
        raise ValueError(f"{LABEL}.native:enum-widths")

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
    for setter in contract["setters"]:
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
                   if member_index+1 < len(contract["orderedReads"])
                   else source_window["endRva"])
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
        actual_digest = hashlib.sha256(data).hexdigest().upper()
        if actual_digest != digest.upper():
            raise ValueError(f"{LABEL}.source:source-hash={path}:expected={digest}:actual={actual_digest}")
        if (ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
                or ledger.get(path, {}).get("length") != len(data)):
            raise ValueError(f"{LABEL}.source:ledger-row={path}:sha256={digest}:length={len(data)}")
        if not 0 <= start < end <= len(data) or data[start:start+2] != prefix:
            raise ValueError(f"{LABEL}.source:union-prefix={path}@{start}:expected={prefix.hex().upper()}")
        actual_span_digest = hashlib.sha256(data[start:end]).hexdigest().upper()
        if actual_span_digest != span_digest.upper():
            raise ValueError(f"{LABEL}.source:span-hash={path}@{start}:expected={span_digest}:actual={actual_span_digest}")
        cursor = _Cursor(data, start)
        tag = cursor.byte("onStartScriptControlledCharMode.tag")
        if tag != route["tag"] or cursor.byte("onStartScriptControlledCharMode.memberCount") != route["serializedMemberCount"]:
            raise ValueError(f"{LABEL}.source:union-header={path}")
        for name, kind in route["fields"]:
            try:
                cursor.value(kind, "onStartScriptControlledCharMode." + name)
            except (ValueError, IndexError) as exc:
                raise ValueError(f"{LABEL}.source:field={path}@{cursor.offset}:{name}:{exc}") from exc
        if cursor.offset != end:
            raise ValueError(f"{LABEL}.source:end-offset={path}")
    return len(contract["sourceReceipts"])


def validate_on_start_script_controlled_char_mode_native_contract(
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
    audit = validate_on_start_script_controlled_char_mode_native_contract(
        game_root=args.game_root, export_root=args.export_root,
        ledger_path=args.ledger, summary_path=args.summary,
    )
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())







