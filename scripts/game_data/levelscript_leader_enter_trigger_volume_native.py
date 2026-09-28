"""Authenticate the stored ScriptEvent.OnLeaderEnterTriggerVolume header route.

The selected switch and generated reader prove the wire layout. Source checks
join each receipt to the current JsonData ledger and replay its exact cursor.
No runtime trigger-volume state or event firing is inferred.

After the inherited script-event header (including `targetScript` and the
`triggerTarget` enum) the route stores `triggerSlotIdFilter` as
`Param<uint>` and a nullable `triggerSlotIdOutput` as `ParamOutput<uint>`.
The contract authenticates the direct switch branch, complete fragmented
generated reader and formatter, ordered reads and setters, and four typed
generic contexts across the inherited and own fields. Reached slot filters
are authored constants and the outputs are null. With the related leave
header also reviewed, the reached race owners close their action maps and a
derived root reaches script ID and physical EOF.

Run as: python -m scripts.game_data.levelscript_leader_enter_trigger_volume_native
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


SCHEMA = "endfield.levelscript-leader-enter-trigger-volume-native-contract.v1"
LABEL = "levelscriptLeaderEnterTriggerVolumeNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_leader_enter_trigger_volume_native.json"


def _contract(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_bytes())
    route = data.get("route", {})
    fields = route.get("fields", [])
    reads = data.get("orderedReads", [])
    setters = data.get("setters", [])
    contexts = data.get("nestedContexts", [])
    if (
        data.get("schema") != SCHEMA
        or data.get("status") != "exact-current-build"
        or data.get("evidenceBoundary") != "exact"
        or route.get("family") != "ActionHeader"
        or route.get("tag") != 0xBF
        or route.get("typeName") != "Beyond.Gameplay.Actions.ScriptEvent.OnLeaderEnterTriggerVolume"
        or route.get("serializedMemberCount") != 18
        or route.get("inheritedMemberCount") != 16
        or len(fields) != 18 or len(route.get("nativeDeclaredTypes", [])) != 18
        or fields[-2:] != [["triggerSlotIdFilter", "Param<uint>"],
                           ["triggerSlotIdOutput", "ParamOutput<uint>"]]
        or len(reads) != 18 or len(setters) != 18
        or [row.get("memberIndex") for row in reads] != list(range(18))
        or [row.get("memberIndex") for row in setters] != list(range(18))
        or [[row.get("fieldName"), row.get("readKind")] for row in reads] != fields
        or [row[0] for row in route["nativeDeclaredTypes"]] != [row[0] for row in fields]
        or set(data.get("readerHelpers", {})) != {kind for _, kind in fields}
        or [row.get("memberIndex") for row in contexts] != [13, 14, 16, 17]
        or [(row.get("baseTypeName"), row.get("elementTypeName")) for row in contexts]
        != [
            ("Beyond.Gameplay.Actions.Param`1", "bool"),
            ("Beyond.Gameplay.Actions.Param`1", "Beyond.Gameplay.Core.LevelScriptPtr"),
            ("Beyond.Gameplay.Actions.Param`1", "uint"),
            ("Beyond.Gameplay.Actions.ParamOutput`1", "uint"),
        ]
        or len(data.get("methods", [])) != 2
        or len(data.get("codeWindows", [])) != 8
        or len(data.get("sourceReceipts", [])) < 1
        or any(len(row) != 7 for row in data["sourceReceipts"])
        or len({(row[0], row[2]) for row in data["sourceReceipts"]}) != len(data["sourceReceipts"])
        or bytes.fromhex(data["memberCountInstruction"]["hex"])[-1] != 18
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return data


def _call_target(image: Any, rva: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:call={rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_context(image: Any, context: dict[str, Any]) -> None:
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    spec_index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if spec_index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:method-spec-index={context['memberIndex']}")
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
        raise ValueError(f"{LABEL}.native:method-spec={context['memberIndex']}")
    instantiation = image.instantiations.resolve(spec[2])
    if len(instantiation.arguments) != 1:
        raise ValueError(f"{LABEL}.native:method-arity={context['memberIndex']}")
    argument = instantiation.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"] or raw[10] != context["typeKind"] != 0x15:
        raise ValueError(f"{LABEL}.native:argument={context['memberIndex']}")
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
        raise ValueError(f"{LABEL}.native:class-carrier={context['memberIndex']}")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    if len(child.arguments) != 1 or child_row != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:class-instantiation={context['memberIndex']}")
    element_argument = child.arguments[0]
    element = bytes.fromhex(element_argument.raw_type_record_hex)
    actual_name = protocol.runtime_type_name(image.pe, image.metadata, element_argument.type_pointer_va)
    expected_kind = {"bool": 0x02, "uint": 0x09}.get(context["elementTypeName"], 0x11)
    if (
        element.hex().upper() != context["elementRawHex"]
        or element[10] != context["elementTypeKind"] != expected_kind
        or actual_name != context["elementTypeName"]
    ):
        raise ValueError(f"{LABEL}.native:param-element={context['memberIndex']}")
    if expected_kind == 0x11:
        definition = struct.unpack_from("<Q", element)[0]
        if definition != context["elementTypeDefinition"] or image.type_name(definition) != actual_name:
            raise ValueError(f"{LABEL}.native:param-value-type={context['memberIndex']}")
    elif context["elementTypeDefinition"] is not None:
        raise ValueError(f"{LABEL}.native:param-primitive={context['memberIndex']}")


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    route = contract["route"]
    dispatch = contract["dispatcher"]
    tag = route["tag"]
    base = image.pe.image_base
    wrappers = derive_from_image(image)
    switch = read_union_switch(
        image, "Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", wrappers=wrappers,
    )
    if (
        switch["entryCount"] != dispatch["switchEntryCount"]
        or not 0 <= tag < switch["entryCount"]
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
    if branch["startRva"] != target or branch["endRva"] <= target:
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
    native_types = [[member.name.lstrip("_"), member.declared_type] for member in wrapper.members]
    normalized = {
        "bool": "bool", "int": "int32", "string": "string",
        "Beyond.GEnums.ScopeName": "int32",
        "Beyond.Gameplay.Actions.FilterLevel": "int32",
        "Beyond.Gameplay.Actions.FilterMask": "int32",
        "Beyond.Gameplay.Actions.TriggerActiveDuring": "int32",
        "Beyond.Gameplay.Actions.Param`1<bool>": "Param<bool>",
        "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.LevelScriptPtr>": "Param<LevelScriptPtr>",
        "Beyond.Gameplay.Actions.ScriptEventHeader+TriggerTarget": "int32",
        "Beyond.Gameplay.Actions.Param`1<uint>": "Param<uint>",
        "Beyond.Gameplay.Actions.ParamOutput`1<uint>": "ParamOutput<uint>",
    }
    if (
        wrapper.name != route["wrapperName"]
        or wrapper.wrapped_type != route["typeName"]
        or len(wrapper.members) != 18
        or len(wrapper.inherited_members) != 16
        or len(wrapper.own_members) != 2
        or native_types != route["nativeDeclaredTypes"]
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
        or not contract["methods"][1][1].startswith(wrapper.name + "+")
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
    count_rva = contract["memberCountInstruction"]["rva"]
    if not any(start <= count_rva < end for start, end in source_ranges):
        raise ValueError(f"{LABEL}.native:member-count-range")
    previous = count_rva
    for read, setter, member in zip(contract["orderedReads"], contract["setters"], wrapper.members):
        i = read["memberIndex"]
        site = read["sourceCallsiteRva"]
        if (
            not previous < site
            or not any(start <= site < end for start, end in source_ranges)
            or _call_target(image, site, read["sourceCallHex"]) != read["sourceTargetRva"]
            or read["sourceTargetRva"] != contract["readerHelpers"][read["readKind"]]
        ):
            raise ValueError(f"{LABEL}.native:ordered-read={i}")
        setter_site = setter["callsiteRva"]
        method_index = setter["methodIndex"]
        method = image.metadata.methods[method_index]
        if (
            member.method_index != method_index
            or member.declaring_wrapper != setter["declaringWrapper"]
            or image.type_name(method.declaring_type) != member.declaring_wrapper
            or image.metadata.string(method.name_index) != setter["setterName"]
            or not site < setter_site < (contract["orderedReads"][i+1]["sourceCallsiteRva"] if i < 17 else max(end for _, end in source_ranges))
            or _call_target(image, setter_site, setter["callHex"]) != setter["targetRva"]
            or image.method_pointer_va(method) != base + setter["targetRva"]
        ):
            raise ValueError(f"{LABEL}.native:setter={i}")
        previous = setter_site
    for context in contract["nestedContexts"]:
        i = context["memberIndex"]
        if not (
            contract["orderedReads"][i-1]["sourceCallsiteRva"]
            < context["instructionRva"]
            < contract["orderedReads"][i]["sourceCallsiteRva"]
        ):
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

    route = contract["route"]
    for path, digest, start, end, span_digest, id_offset, script_id in contract["sourceReceipts"]:
        data = (export_root / path).read_bytes()
        if (
            not 0 <= start < end <= len(data)
            or not 0 <= id_offset <= len(data)-8
            or data[start:start+2] != bytes((route["tag"], route["serializedMemberCount"]))
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
            or ledger.get(path, {}).get("length") != len(data)
            or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
            or int.from_bytes(data[id_offset:id_offset+8], "little") != script_id
            or not Path(path).stem.isdecimal() or int(Path(path).stem) != script_id
        ):
            raise ValueError(f"{LABEL}.source:receipt={path}")
        cursor = _Cursor(data, start)
        if cursor.byte("leaderEnterTriggerVolume.tag") != route["tag"] or cursor.byte("leaderEnterTriggerVolume.memberCount") != 18:
            raise ValueError(f"{LABEL}.source:union-header={path}")
        for name, kind in route["fields"]:
            cursor.value(kind, "leaderEnterTriggerVolume." + name)
        if cursor.offset != end:
            raise ValueError(f"{LABEL}.source:end-offset={path}")
    return len(contract["sourceReceipts"])


def validate_leader_enter_trigger_volume_native_contract(
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
    audit = validate_leader_enter_trigger_volume_native_contract(
        game_root=args.game_root, export_root=args.export_root,
        ledger_path=args.ledger, summary_path=args.summary,
    )
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())

