"""Authenticate the current StartLevelSeqLoopSegment ActionBase stored layout.

This is a selected-build contract, so a missing or different installed client
returns no route. The optional source check joins every reviewed cursor to the
JsonData per-file ledger before treating it as a current exported example.

After the inherited action fields the branch stores `levelSeqId` and
`loopSegmentName` as `Param<string>`, `segmentList` as
`Param<List<string>>` and `setMultipleSegment` as `Param<bool>`. The
contract checks the switch jump and registered wrapper, full reader and
formatter extents, twelve ordered reads, four setters, and the nested
generic contexts down to the list's string element. Reached records are
wide-tagged. Stored loop settings do not show that a sequence ran.

The command takes no options and prints the native audit only, exiting
nonzero unless it validates. The source check goes through
`validate_start_seq_loop_native_contract`, which accepts an explicit export
root and JsonData per-file ledger.

Run as: python -m scripts.game_data.levelscript_start_seq_loop_native
"""

from __future__ import annotations

import gzip
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import (
    generic_type_carrier,
    method_spec_record,
    method_spec_usage_index,
    unresolved_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-start-level-seq-loop-segment-native-contract.v1"
LABEL = "levelscriptStartSeqLoopNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_start_seq_loop_native.json"


def _contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    if contract.get("schema") != SCHEMA:
        raise ValueError(f"{LABEL}.contract:schema")
    if contract.get("status") != "exact-current-build" or contract.get("evidenceBoundary") != "exact":
        raise ValueError(f"{LABEL}.contract:status-boundary")
    route = contract["route"]
    fields = route["fields"]
    reads = contract["orderedReads"]
    contexts = contract["nestedContexts"]
    setters = contract["ownSetters"]
    expected_elements = {
        "Param<string>": "System.String",
        "Param<List<string>>": "System.Collections.Generic.List`1",
        "Param<bool>": "System.Boolean",
    }
    if (
        route.get("family") != "ActionBase"
        or not isinstance(route.get("tag"), int)
        or not 0xFA <= route["tag"] < min(contract["dispatcher"]["switchEntryCount"], 0x10000)
        or route.get("serializedMemberCount") != len(fields)
        or not isinstance(route.get("inheritedMemberCount"), int)
        or not 0 <= route["inheritedMemberCount"] <= len(fields)
        or not all(isinstance(row, list) and len(row) == 2
                   and all(isinstance(part, str) and part for part in row) for row in fields)
        or [row["memberIndex"] for row in reads] != list(range(len(fields)))
        or [(row["fieldName"], row["readKind"]) for row in reads]
        != [tuple(field) for field in fields]
        or [row["memberIndex"] for row in contexts]
        != list(range(route["inheritedMemberCount"], len(fields)))
        or [row["elementTypeName"] for row in contexts]
        != [expected_elements.get(field[1]) for field in fields[route["inheritedMemberCount"]:]]
        or None in [row["elementTypeName"] for row in contexts]
        or [row["memberIndex"] for row in setters]
        != list(range(route["inheritedMemberCount"], len(fields)))
        or [row["setterName"] for row in setters]
        != [f"set____{field[0]}__" for field in fields[route["inheritedMemberCount"]:]]
        or len(contract["methods"]) != 2 or len(contract["codeWindows"]) != 2
        or contract["methods"][0][1] != route["wrapperName"]
        or not contract["methods"][1][1].startswith(route["wrapperName"] + "+")
        or [row[2] for row in contract["methods"]] != ["Deserialize", "Deserialize"]
        or bytes.fromhex(contract["memberCountInstruction"]["hex"])[-1] != len(fields)
        or len(contract["sourceReceipts"]) < 1
        or len({row[0] for row in contract["sourceReceipts"]}) != len(contract["sourceReceipts"])
        or any(len(row) != 5 for row in contract["sourceReceipts"])
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def _call_target(image: Any, site: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:call={site:#x}")
    return site + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_context(image: Any, context: dict[str, Any], expected_type: str) -> None:
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    spec_index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if spec_index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:param-spec-index={context['memberIndex']}")
    address = int(image.registration["methodSpecs"], 16) + spec_index * 12
    spec = method_spec_record(
        image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source=LABEL, offset=address,
    )
    method = image.metadata.methods[spec[0]]
    if (
        image.metadata.string(method.name_index) != "ReadValue"
        or image.type_name(method.declaring_type) != "MemoryPack.MemoryPackReader"
    ):
        raise ValueError(f"{LABEL}.native:param-reader-method={context['memberIndex']}")
    instantiation = image.instantiations.resolve(spec[2])
    if list(spec) != context["methodSpec"] or len(instantiation.arguments) != 1:
        raise ValueError(f"{LABEL}.native:param-spec={context['memberIndex']}")
    argument = instantiation.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"] or raw[10] != 0x15:
        raise ValueError(f"{LABEL}.native:param-generic-type={context['memberIndex']}")
    carrier_pointer = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(carrier_pointer, 32)
    base_raw = image.pe.bytes_at_va(struct.unpack_from("<Q", carrier_raw)[0], 16)
    carrier = generic_type_carrier(
        raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
        type_count=len(image.metadata.types), source=LABEL,
    )
    if (carrier != context["classCarrier"]
            or image.type_name(carrier["baseDefinitionIndex"])
            != "Beyond.Gameplay.Actions.Param`1"):
        raise ValueError(f"{LABEL}.native:param-carrier={context['memberIndex']}")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    if child_row != context["classInstantiation"] or len(child.arguments) != 1:
        raise ValueError(f"{LABEL}.native:param-instantiation={context['memberIndex']}")
    element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
    if (element.hex().upper() != context["elementRawHex"]
            or element[10] != context["elementTypeKind"]
            or context["elementTypeName"] != expected_type):
        raise ValueError(f"{LABEL}.native:param-element={context['memberIndex']}")
    if expected_type == "System.Boolean":
        if element[10] != 2 or context["elementTypeDefinition"] is not None:
            raise ValueError(f"{LABEL}.native:param-bool={context['memberIndex']}")
    elif expected_type == "System.String":
        if element[10] != 14 or context["elementTypeDefinition"] is not None:
            raise ValueError(f"{LABEL}.native:param-string={context['memberIndex']}")
    else:
        if (expected_type != "System.Collections.Generic.List`1"
                or element[10] != 0x15 or context["elementTypeDefinition"] is not None):
            raise ValueError(f"{LABEL}.native:param-list-kind={context['memberIndex']}")
        nested_pointer = struct.unpack_from("<Q", element)[0]
        nested_raw = image.pe.bytes_at_va(nested_pointer, 32)
        nested_base_raw = image.pe.bytes_at_va(struct.unpack_from("<Q", nested_raw)[0], 16)
        nested_carrier = generic_type_carrier(
            element, nested_raw, nested_base_raw,
            type_pointer=child.arguments[0].type_pointer_va,
            type_count=len(image.metadata.types), source=LABEL,
        )
        nested_instantiation = image.instantiations.resolve_pointer(
            nested_carrier["classInstantiationPointerVa"]
        )
        nested_row = nested_instantiation.as_dict()
        nested_row["arguments"] = list(nested_row["arguments"])
        nested = context["nestedGeneric"]
        if (
            nested_pointer != context["elementPointerVa"]
            or image.type_name(nested_carrier["baseDefinitionIndex"]) != expected_type
            or nested_carrier != nested["carrier"]
            or nested_row != nested["classInstantiation"]
            or len(nested_instantiation.arguments) != 1
            or bytes.fromhex(nested_instantiation.arguments[0].raw_type_record_hex)[10] != 14
            or nested["innerTypeName"] != "System.String"
        ):
            raise ValueError(f"{LABEL}.native:param-list-string={context['memberIndex']}")


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    route = contract["route"]
    branch = contract["dispatcher"]
    base = image.pe.image_base
    wrappers = derive_from_image(image)
    switch = read_union_switch(
        image, "Beyond_Gameplay_Actions_ActionBaseForMemoryPack", wrappers=wrappers,
    )
    tag = route["tag"]
    entry = switch["entries"][tag]
    if (
        switch["entryCount"] != branch["switchEntryCount"]
        or int(switch["tableVa"], 16) != base + branch["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-shape")
    table = image.pe.bytes_at_va(base + branch["switchTableRva"], switch["entryCount"] * 4)
    if hashlib.sha256(table).hexdigest().upper() != branch["switchTableSha256"].upper():
        raise ValueError(f"{LABEL}.native:switch-hash")
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
    if load[:3] != b"\x48\x8B\x15" or load.hex().upper() != branch["typeLoadHex"].upper():
        raise ValueError(f"{LABEL}.native:type-load")
    usage_cell = base + load_site + 7 + struct.unpack_from("<i", load, 3)[0]
    usage = image.pe.bytes_at_va(usage_cell, 8)
    index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1, source=LABEL, offset=usage_cell,
    )
    if (
        usage_cell - base != branch["usageCellRva"]
        or usage.hex().upper() != branch["usageRawHex"].upper()
        or index != route["registeredTypeIndex"]
    ):
        raise ValueError(f"{LABEL}.native:wrapper-usage")
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    definition = struct.unpack_from("<Q", image.pe.bytes_at_va(pointer, 16))[0]
    if definition != route["typeDefinition"] or image.type_name(definition) != route["wrapperName"]:
        raise ValueError(f"{LABEL}.native:registered-wrapper")
    wrapper = wrappers[definition]
    normalized_kinds = {
        "bool": "bool", "int": "int32", "string": "string",
        "Beyond.GEnums.ScopeName": "int32",
        "Beyond.Gameplay.Actions.Param`1<string>": "Param<string>",
        "Beyond.Gameplay.Actions.Param`1<System.Collections.Generic.List`1<string>>": "Param<List<string>>",
        "Beyond.Gameplay.Actions.Param`1<bool>": "Param<bool>",
    }
    if (
        wrapper.wrapped_type != route["typeName"]
        or len(wrapper.members) != route["serializedMemberCount"]
        or len(wrapper.members) - len(wrapper.own_members) != route["inheritedMemberCount"]
        or [[member.name.lstrip("_"), normalized_kinds.get(member.declared_type)]
            for member in wrapper.members] != route["fields"]
        or any(
            member.kind != "enum" or member.underlying_kind != "scalar32" or member.width != 4
            for member in wrapper.members if member.declared_type == "Beyond.GEnums.ScopeName"
        )
    ):
        raise ValueError(f"{LABEL}.native:wrapper-fields")

    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    windows = contract["codeWindows"]
    image.check_windows(windows, label=LABEL)
    count = contract["memberCountInstruction"]
    image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
    extents = image.mapper.pdata_function_extents(image.pe)
    for method_index, window in zip(methods, windows):
        pointer = image.method_pointer_va(image.metadata.methods[method_index])
        if (
            window["startRva"] != pointer - base
            or window["endRva"] != extents.get(pointer, 0) - base
        ):
            raise ValueError(f"{LABEL}.native:method-extent")
    source_window = windows[0]
    if not source_window["startRva"] < count["rva"] < source_window["endRva"]:
        raise ValueError(f"{LABEL}.native:member-count-range")
    previous = count["rva"]
    for read in contract["orderedReads"]:
        site = read["sourceCallsiteRva"]
        if not previous < site < source_window["endRva"]:
            raise ValueError(f"{LABEL}.native:read-order={read['memberIndex']}")
        if _call_target(image, site, read["sourceCallHex"]) != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:read-target={read['memberIndex']}")
        previous = site
    for setter in contract["ownSetters"]:
        member_index = setter["memberIndex"]
        member = wrapper.members[member_index]
        method_index = setter["methodIndex"]
        method = image.metadata.methods[method_index]
        if (
            member.method_index != method_index
            or member.declaring_wrapper != setter["declaringWrapper"]
            or image.metadata.string(method.name_index) != setter["setterName"]
            or image.method_pointer_va(method) != base + setter["targetRva"]
            or not contract["orderedReads"][member_index]["sourceCallsiteRva"]
            < setter["callsiteRva"]
            < (contract["orderedReads"][member_index + 1]["sourceCallsiteRva"]
               if member_index + 1 < len(contract["orderedReads"]) else source_window["endRva"])
            or _call_target(image, setter["callsiteRva"], setter["callHex"])
            != setter["targetRva"]
        ):
            raise ValueError(f"{LABEL}.native:setter={member_index}")
    for context in contract["nestedContexts"]:
        member_index = context["memberIndex"]
        prior = contract["orderedReads"][member_index - 1]["sourceCallsiteRva"]
        current = contract["orderedReads"][member_index]["sourceCallsiteRva"]
        if not prior < context["instructionRva"] < current:
            raise ValueError(f"{LABEL}.native:param-context-order={member_index}")
        _validate_context(image, context, context["elementTypeName"])


def _validate_sources(contract: dict[str, Any], export_root: Path, ledger_path: Path) -> None:
    tag = contract["route"]["tag"]
    member_count = contract["route"]["serializedMemberCount"]
    prefix = b"\xfa" + tag.to_bytes(2, "little") + bytes((member_count,))
    ledger: dict[str, dict[str, Any]] = {}
    with gzip.open(ledger_path, "rt", encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData":
                ledger[row["exportRelativePath"]] = row
    if not ledger:
        raise ValueError(f"{LABEL}.source:missing-LevelScript-ledger")
    for path, digest, start, end, span_digest in contract["sourceReceipts"]:
        data = (export_root / path).read_bytes()
        if (
            not 0 <= start < end <= len(data)
            or data[start:start + 4] != prefix
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
            or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
        ):
            raise ValueError(f"{LABEL}.source:receipt={path}")


def validate_start_seq_loop_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Prove native route and, when requested, all pinned source receipts."""
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
            return {"status": "validation_failed", "failedCheck": "installed-native-inputs",
                    "nativeStatus": gate.status, "detail": gate.detail,
                    "validationFailures": [{"gate": "installed_native_inputs"}]}
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        if not unity.is_file() or sha256_file(unity).upper() != expected["UnityPlayer.dll"].upper():
            raise ValueError(f"{LABEL}.native:UnityPlayer.dll")
        image = open_native_image(gate.gameassembly, gate.metadata)
        _validate_native(image, contract)
        if export_root is not None:
            if ledger_path is None:
                raise ValueError(f"{LABEL}.source:explicit-ledger-required")
            _validate_sources(contract, Path(export_root), Path(ledger_path))
        return {"status": "validated", "evidenceBoundary": "exact",
                "route": {"family": contract["route"]["family"],
                          "tag": contract["route"]["tag"],
                          "wrapperName": contract["route"]["wrapperName"],
                          "fields": contract["route"]["fields"]},
                "sourceReceiptsChecked": len(contract["sourceReceipts"]) if export_root else 0}
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as exc:
        failure = str(exc)
        check = (failure.split(".contract:", 1)[1] if ".contract:" in failure
                 else failure.split(".native:", 1)[1] if ".native:" in failure
                 else failure.split(".source:", 1)[1] if ".source:" in failure
                 else "contract-native-or-source")
        return {"status": "validation_failed", "failedCheck": check,
                "detail": failure,
                "validationFailures": [{"gate": check, "actual": failure[:500]}]}


def main() -> int:
    audit = validate_start_seq_loop_native_contract()
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
