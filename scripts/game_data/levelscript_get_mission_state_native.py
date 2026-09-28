"""Authenticate the selected GetMissionState PureGetter stored layout.

The native and exported-source checks establish serialized bytes. They do not
establish when the getter evaluates or which synchronized mission state wins.

The branch inherits seven node fields and adds `missionId` as
`Param<string>`. The contract checks the dispatcher and registered wrapper,
complete chained reader and forwarding formatter bodies, eight ordered
native reads and setters, and the string parameter's generic context.

The command takes no options and prints the native audit only, exiting
nonzero unless it validates. Source cursor replay goes through
`validate_get_mission_state_native_contract`, which accepts an explicit
JsonData export root, per-file ledger and summary.

Run as: python -m scripts.game_data.levelscript_get_mission_state_native
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
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import (
    generic_type_carrier,
    method_spec_record,
    method_spec_usage_index,
    unresolved_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-get-mission-state-native-contract.v1"
LABEL = "levelscriptGetMissionStateNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_get_mission_state_native.json"


def _contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    route = contract.get("route") or {}
    fields = route.get("fields")
    reads = contract.get("readOrder")
    context = contract.get("paramContext") or {}
    if (
        contract.get("schema") != SCHEMA
        or contract.get("status") != "exact-current-build"
        or contract.get("evidenceBoundary") != "exact"
        or route.get("family") != "GetterBase"
        or route.get("nativeFamily") != "PureGetter"
        or not isinstance(route.get("tag"), int)
        or not 0xFA <= route["tag"] < contract.get("dispatcher", {}).get("switchEntryCount", 0)
        or not isinstance(route.get("typeName"), str)
        or not route["typeName"]
        or not isinstance(fields, list)
        or not 1 < len(fields) < 256
        or route.get("memberCount") != len(fields)
        or route.get("inheritedMemberCount") != len(fields)-1
        or any(not isinstance(row, list) or len(row) != 3
               or not all(isinstance(part, str) and part for part in row)
               for row in fields)
        or fields[-1][1] != "Param<string>"
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(fields)))
        or [(row.get("fieldName"), row.get("readKind")) for row in reads]
        != [(row[0], row[1]) for row in fields]
        or context.get("memberIndex") != len(fields)-1
        or context.get("elementTypeName") != "System.String"
        or not isinstance(contract.get("codeWindows"), list)
        or len(contract["codeWindows"]) < 3
        or not isinstance(contract.get("methods"), list)
        or len(contract["methods"]) != 2
        or contract["methods"][0][1] != route.get("wrapperName")
        or not contract["methods"][1][1].startswith(route.get("wrapperName", "") + "+")
        or [row[2] for row in contract["methods"]] != ["Deserialize", "Deserialize"]
        or contract.get("formatterTailJump", {}).get("targetRva") != contract["methods"][0][3]
        or bytes.fromhex(contract["memberCountInstruction"]["hex"])[-1] != len(fields)
        or not isinstance(contract.get("sourceReceipts"), list)
        or not contract["sourceReceipts"]
        or any(not isinstance(row, list) or len(row) != 5 for row in contract["sourceReceipts"])
        or len({(row[0], row[2]) for row in contract["sourceReceipts"]}) != len(contract["sourceReceipts"])
    ):
        raise ValueError(f"{LABEL}.contract:route-shape")
    return contract


def _call_target(image: Any, site: int, expected_hex: str) -> int:
    code = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if code[0] != 0xE8 or code.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:callsite={site:#x}")
    return site + 5 + struct.unpack_from("<i", code, 1)[0]


def _validate_param_string_context(image: Any, context: dict[str, Any]) -> None:
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
        image.metadata.string(method.name_index) != "ReadValue"
        or image.type_name(method.declaring_type) != "MemoryPack.MemoryPackReader"
        or list(spec) != context["methodSpec"]
    ):
        raise ValueError(f"{LABEL}.native:param-reader-method")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:param-spec-arity")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"].upper() or raw[10] != 0x15:
        raise ValueError(f"{LABEL}.native:param-generic-type")
    carrier_pointer = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(carrier_pointer, 32)
    base_raw = image.pe.bytes_at_va(struct.unpack_from("<Q", carrier_raw)[0], 16)
    carrier = generic_type_carrier(
        raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
        type_count=len(image.metadata.types), source=LABEL,
    )
    if (
        carrier != context["classCarrier"]
        or image.type_name(carrier["baseDefinitionIndex"])
        != "Beyond.Gameplay.Actions.Param`1"
    ):
        raise ValueError(f"{LABEL}.native:param-carrier")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    if len(child.arguments) != 1 or child_row != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:param-instantiation")
    element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
    if (
        element.hex().upper() != context["elementRawHex"].upper()
        or element[10] != 14
        or context["elementTypeKind"] != 14
        or context["elementTypeDefinition"] is not None
    ):
        raise ValueError(f"{LABEL}.native:param-string-element")


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    base = image.pe.image_base
    route = contract["route"]
    branch = contract["dispatcher"]
    wrappers = derive_from_image(image)
    switch = read_union_switch(
        image, "Beyond_Gameplay_Actions_PureGetterForMemoryPack", wrappers=wrappers,
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
        target != branch["switchTargetRva"]
        or jump[0] != 0xE9
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
    if (
        wrapper.wrapped_type != route["typeName"]
        or len(wrapper.inherited_members) != route["inheritedMemberCount"]
        or len(wrapper.members) != route["memberCount"]
        or [[m.name.lstrip("_"), m.declared_type] for m in wrapper.members]
        != [[row[0], row[2]] for row in route["fields"]]
        or any(
            m.kind != "enum" or m.underlying_kind != "scalar32" or m.width != 4
            for m in wrapper.members if m.declared_type == "Beyond.GEnums.ScopeName"
        )
    ):
        raise ValueError(f"{LABEL}.native:wrapper-fields")

    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    windows = contract["codeWindows"]
    image.check_windows(windows, label=LABEL)
    extents = image.mapper.pdata_function_extents(image.pe)
    source = image.method_pointer_va(image.metadata.methods[methods[0]])
    formatter = image.method_pointer_va(image.metadata.methods[methods[1]])
    fragments = BodyIndex(image).chained_fragments.get(source, ())
    expected_windows = [
        (source-base, extents[source]-base),
        *((va-base, va+length-base) for va, length in fragments),
        (formatter-base, extents[formatter]-base),
    ]
    if [(window["startRva"], window["endRva"]) for window in windows] != expected_windows:
        raise ValueError(f"{LABEL}.native:complete-method-windows")
    tail = contract["formatterTailJump"]
    tail_code = image.pe.bytes_at_va(base + tail["instructionRva"], 5)
    if (
        not windows[-1]["startRva"] <= tail["instructionRva"] < windows[-1]["endRva"]
        or tail_code[0] != 0xE9
        or tail_code.hex().upper() != tail["instructionHex"].upper()
        or tail["instructionRva"] + 5 + struct.unpack_from("<i", tail_code, 1)[0]
        != tail["targetRva"]
    ):
        raise ValueError(f"{LABEL}.native:formatter-forwarding")
    count = contract["memberCountInstruction"]
    image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
    if count["hex"].upper() != f"4080FE{route['memberCount']:02X}":
        raise ValueError(f"{LABEL}.native:member-count")
    source_ranges = [(window["startRva"], window["endRva"]) for window in windows[:-1]]
    previous = count["rva"]
    for read in contract["readOrder"]:
        site, setter_site = read["readCallRva"], read["setterCallRva"]
        member = wrapper.members[read["memberIndex"]]
        setter = image.metadata.methods[member.method_index]
        if (
            not previous < site < setter_site
            or not any(start <= site < setter_site < end for start, end in source_ranges)
            or _call_target(image, site, read["readCallHex"]) != read["readTargetRva"]
            or _call_target(image, setter_site, read["setterCallHex"]) != read["setterTargetRva"]
            or member.method_index != read["setterMethodIndex"]
            or member.declaring_wrapper != read["declaringWrapper"]
            or image.metadata.string(setter.name_index) != f"set___{member.name}__"
            or image.method_pointer_va(setter) != base + read["setterTargetRva"]
        ):
            raise ValueError(f"{LABEL}.native:ordered-read-setter={read['memberIndex']}")
        previous = setter_site
    context = contract["paramContext"]
    if not (
        contract["readOrder"][-2]["setterCallRva"]
        < context["instructionRva"] < contract["readOrder"][-1]["readCallRva"]
    ):
        raise ValueError(f"{LABEL}.native:param-context-order")
    _validate_param_string_context(image, context)


def _validate_sources(
    contract: dict[str, Any], export_root: Path, ledger_path: Path, summary_path: Path,
) -> int:
    summary = json.loads(summary_path.read_bytes())
    if (
        summary.get("status") != "complete"
        or hashlib.sha256(ledger_path.read_bytes()).hexdigest().upper()
        != summary.get("provenance", {}).get("outputFiles", {}).get("sha256", "").upper()
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
    route = contract["route"]
    prefix = b"\xFA" + route["tag"].to_bytes(2, "little") + bytes((route["memberCount"],))
    for path, digest, start, end, span_digest in contract["sourceReceipts"]:
        data = (export_root / path).read_bytes()
        if (
            not 0 <= start < end <= len(data)
            or data[start:start+4] != prefix
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
            or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
            or ledger.get(path, {}).get("length") != len(data)
        ):
            raise ValueError(f"{LABEL}.source:receipt={path},offset={start}")
    return len(contract["sourceReceipts"])


def validate_get_mission_state_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Return the selected route only after current native and optional source checks."""
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
            return {
                "status": "validation_failed", "failedCheck": "installed-native-inputs",
                "nativeStatus": gate.status, "detail": gate.detail,
                "validationFailures": [{"gate": "installed_native_inputs"}],
            }
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        if not unity.is_file() or sha256_file(unity).upper() != expected["UnityPlayer.dll"].upper():
            raise ValueError(f"{LABEL}.native:UnityPlayer.dll")
        image = open_native_image(gate.gameassembly, gate.metadata)
        _validate_native(image, contract)
        checked = 0
        if export_root is not None:
            if ledger_path is None or summary_path is None:
                raise ValueError(f"{LABEL}.source:explicit-summary-and-ledger-required")
            checked = _validate_sources(
                contract, Path(export_root), Path(ledger_path), Path(summary_path),
            )
        route = contract["route"]
        return {
            "status": "validated", "evidenceBoundary": "exact",
            "route": {
                "family": route["family"], "tag": route["tag"],
                "wrapperName": route["wrapperName"],
                "fields": [field[:2] for field in route["fields"]],
            },
            "sourceReceiptsChecked": checked,
        }
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as exc:
        failure = str(exc)
        check = (
            failure.split(".contract:", 1)[1] if ".contract:" in failure
            else failure.split(".native:", 1)[1] if ".native:" in failure
            else failure.split(".source:", 1)[1] if ".source:" in failure
            else "contract-native-or-source"
        )
        return {
            "status": "validation_failed", "failedCheck": check, "detail": failure,
            "validationFailures": [{"gate": check, "actual": failure[:500]}],
        }


def main() -> int:
    audit = validate_get_mission_state_native_contract()
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
