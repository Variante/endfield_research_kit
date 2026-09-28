"""Authenticate TyphoeaArcherySetChipId's selected ActionBase stored layout.

The installed switch, complete Deserialize bodies, ten ordered read/setter
pairs, and two Param<string> contexts establish stored fields. They do not
establish runtime chip selection.
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
from scripts.game_data.il2cpp import protocol as il2cpp
from scripts.game_data.il2cpp.context import (
    generic_type_carrier, method_spec_record, method_spec_usage_index,
    unresolved_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-typhoea-chip-id-native-contract.v1"
LABEL = "levelscriptTyphoeaChipIdNative"
CONTRACT_PATH = CONTRACTS_DIR / "levelscript_typhoea_chip_id_native.json"
_KINDS = ["bool", "int32", "bool", "string", "int32", "bool", "bool", "int32",
          "Param<string>", "Param<string>"]
_NATIVE = ["bool", "int", "bool", "string", "Beyond.GEnums.ScopeName", "bool",
           "bool", "int", "Beyond.Gameplay.Actions.Param`1<string>",
           "Beyond.Gameplay.Actions.Param`1<string>"]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _contract(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_bytes())
    route = data.get("route", {})
    fields = route.get("fields", [])
    reads = data.get("readOrder", [])
    contexts = data.get("paramContexts", [])
    if (
        data.get("schema") != SCHEMA or data.get("status") != "exact-current-build"
        or data.get("evidenceBoundary") != "exact"
        or set(data.get("nativeInputs", {})) != {"GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll"}
        or route.get("family") != "ActionBase" or route.get("tag") != 0x04FA
        or route.get("typeName") != "Beyond.Gameplay.Actions.TyphoeaArcherySetChipId"
        or route.get("memberCount") != 10 or route.get("inheritedMemberCount") != 8
        or not isinstance(fields, list) or len(fields) != 10
        or any(not isinstance(row, list) or len(row) != 3 for row in fields)
        or [row[1] for row in fields] != _KINDS
        or [row[2] for row in fields] != _NATIVE
        or [row[0] for row in fields[8:]] != ["mainChipId", "subChipId"]
        or [row.get("memberIndex") for row in reads] != list(range(10))
        or [(row.get("fieldName"), row.get("readKind")) for row in reads]
        != [(row[0], row[1]) for row in fields]
        or set(data.get("readerHelpers", {})) != set(_KINDS)
        or any(row.get("readTargetRva") != data["readerHelpers"].get(row["readKind"])
               for row in reads)
        or [row.get("memberIndex") for row in contexts] != [8, 9]
        or [row.get("elementTypeName") for row in contexts] != ["System.String"] * 2
        or any(row.get("elementTypeKind") != 14 for row in contexts)
        or len(data.get("methods", [])) != 2 or len(data.get("codeWindows", [])) != 2
        or data["methods"][0][1] != route.get("wrapperName")
        or not data["methods"][1][1].startswith(route["wrapperName"] + "+")
        or [row[2] for row in data["methods"]] != ["Deserialize", "Deserialize"]
        or data.get("formatterTailJump", {}).get("targetRva") != data["methods"][0][3]
        or bytes.fromhex(data["memberCountInstruction"]["hex"])[-1] != 10
        or len(data.get("sourceReceipts", [])) < 1
        or any(len(row) != 5 for row in data["sourceReceipts"])
        or len({(row[0], row[2]) for row in data["sourceReceipts"]}) != len(data["sourceReceipts"])
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return data


def _call_target(image: Any, site: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:callsite={site:#x}")
    return site + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_context(image: Any, context: dict[str, Any]) -> None:
    member = context["memberIndex"]
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:param-spec-index={member}")
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
        raise ValueError(f"{LABEL}.native:param-reader-method={member}")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:param-spec-arity={member}")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"].upper() or raw[10] != 0x15:
        raise ValueError(f"{LABEL}.native:param-generic-type={member}")
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
        raise ValueError(f"{LABEL}.native:param-carrier={member}")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    if len(child.arguments) != 1 or child_row != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:param-instantiation={member}")
    element = child.arguments[0]
    element_raw = bytes.fromhex(element.raw_type_record_hex)
    if (
        element_raw.hex().upper() != context["elementRawHex"].upper()
        or element_raw[10] != context["elementTypeKind"] or element_raw[10] != 14
        or il2cpp.runtime_type_name(image.pe, image.metadata, element.type_pointer_va) != "string"
        or context["elementTypeName"] != "System.String"
    ):
        raise ValueError(f"{LABEL}.native:param-string={member}")


def _validate_native(image: Any, data: dict[str, Any]) -> None:
    base = image.pe.image_base
    route, dispatcher = data["route"], data["dispatcher"]
    wrappers = derive_from_image(image)
    switch = read_union_switch(
        image, "Beyond_Gameplay_Actions_ActionBaseForMemoryPack", wrappers=wrappers,
    )
    if (
        switch["entryCount"] != dispatcher["switchEntryCount"]
        or int(switch["tableVa"], 16) != base + dispatcher["switchTableRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-shape")
    table = image.pe.bytes_at_va(base + dispatcher["switchTableRva"], switch["entryCount"] * 4)
    if _sha(table) != dispatcher["switchTableSha256"].upper():
        raise ValueError(f"{LABEL}.native:switch-table-hash")
    tag = route["tag"]
    target = struct.unpack_from("<I", table, tag * 4)[0]
    jump = image.pe.bytes_at_va(base + target, 5)
    entry = switch["entries"][tag]
    if (
        target != dispatcher["switchTargetRva"] or jump[0] != 0xE9
        or jump.hex().upper() != dispatcher["switchEntryHex"].upper()
        or target + 5 + struct.unpack_from("<i", jump, 1)[0] != dispatcher["bodyRva"]
        or int(entry["targetVa"], 16) != base + target
        or int(entry["bodyVa"], 16) != base + dispatcher["bodyRva"]
        or entry["wrapperName"] != route["wrapperName"]
        or entry["typeDefinition"] != route["typeDefinition"]
        or entry["registeredTypeIndex"] != route["registeredTypeIndex"]
    ):
        raise ValueError(f"{LABEL}.native:dispatch-entry")
    image.check_windows([dispatcher["branchWindow"]], label=LABEL)
    load = image.pe.bytes_at_va(base + dispatcher["typeLoadRva"], 7)
    if load[:3] != b"\x48\x8B\x15" or load.hex().upper() != dispatcher["typeLoadHex"].upper():
        raise ValueError(f"{LABEL}.native:type-load")
    cell = base + dispatcher["typeLoadRva"] + 7 + struct.unpack_from("<i", load, 3)[0]
    usage = image.pe.bytes_at_va(cell, 8)
    index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1, source=LABEL, offset=cell,
    )
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    definition = struct.unpack_from("<Q", image.pe.bytes_at_va(pointer, 16))[0]
    if (
        cell - base != dispatcher["usageCellRva"]
        or usage.hex().upper() != dispatcher["usageRawHex"].upper()
        or index != route["registeredTypeIndex"] or definition != route["typeDefinition"]
        or image.type_name(definition) != route["wrapperName"]
    ):
        raise ValueError(f"{LABEL}.native:registered-wrapper")
    wrapper = wrappers[definition]
    if (
        wrapper.wrapped_type != route["typeName"]
        or len(wrapper.inherited_members) != route["inheritedMemberCount"]
        or len(wrapper.members) != route["memberCount"]
        or [[m.name.lstrip("_"), m.declared_type] for m in wrapper.members]
        != [[row[0], row[2]] for row in route["fields"]]
        or any(m.kind != "enum" or m.underlying_kind != "scalar32" or m.width != 4
               for m in wrapper.members if m.declared_type == "Beyond.GEnums.ScopeName")
    ):
        raise ValueError(f"{LABEL}.native:wrapper-fields")
    methods = [image.validate_method_row(row, label=LABEL) for row in data["methods"]]
    windows = data["codeWindows"]
    image.check_windows(windows, label=LABEL)
    extents = image.mapper.pdata_function_extents(image.pe)
    for method_index, window in zip(methods, windows):
        pointer = image.method_pointer_va(image.metadata.methods[method_index])
        if (pointer-base, extents.get(pointer, 0)-base) != (window["startRva"], window["endRva"]):
            raise ValueError(f"{LABEL}.native:method-extent={method_index}")
    tail = data["formatterTailJump"]
    code = image.pe.bytes_at_va(base + tail["instructionRva"], 5)
    if (
        not windows[1]["startRva"] <= tail["instructionRva"] < windows[1]["endRva"]
        or code[0] != 0xE9 or code.hex().upper() != tail["instructionHex"].upper()
        or tail["instructionRva"] + 5 + struct.unpack_from("<i", code, 1)[0] != tail["targetRva"]
    ):
        raise ValueError(f"{LABEL}.native:formatter-forwarding")
    count = data["memberCountInstruction"]
    image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
    if count["hex"].upper() != "807C24380A" or not windows[0]["startRva"] < count["rva"] < windows[0]["endRva"]:
        raise ValueError(f"{LABEL}.native:member-count")
    previous = count["rva"]
    for read in data["readOrder"]:
        member_index = read["memberIndex"]
        member = wrapper.members[member_index]
        setter_method = image.metadata.methods[member.method_index]
        read_site, setter_site = read["readCallRva"], read["setterCallRva"]
        if (
            not previous < read_site < setter_site < windows[0]["endRva"]
            or _call_target(image, read_site, read["readCallHex"]) != read["readTargetRva"]
            or _call_target(image, setter_site, read["setterCallHex"]) != read["setterTargetRva"]
            or member.method_index != read["setterMethodIndex"]
            or member.declaring_wrapper != read["declaringWrapper"]
            or image.metadata.string(setter_method.name_index) != read["setterName"]
            or image.method_pointer_va(setter_method) != base + read["setterTargetRva"]
        ):
            raise ValueError(f"{LABEL}.native:ordered-read-setter={member_index}")
        previous = setter_site
    for context in data["paramContexts"]:
        index = context["memberIndex"]
        if not data["readOrder"][index-1]["setterCallRva"] < context["instructionRva"] < data["readOrder"][index]["readCallRva"]:
            raise ValueError(f"{LABEL}.native:param-context-order={index}")
        _validate_context(image, context)


def _validate_sources(data: dict[str, Any], export_root: Path, ledger_path: Path,
                      summary_path: Path) -> int:
    from scripts.game_data.codecs.levelscript.typhoea_chip_id import decode_typhoea_chip_id_action

    summary = json.loads(summary_path.read_bytes())
    if (
        summary.get("status") != "complete"
        or _sha(ledger_path.read_bytes())
        != summary.get("provenance", {}).get("outputFiles", {}).get("sha256", "").upper()
    ):
        raise ValueError(f"{LABEL}.source:summary-ledger-join")
    ledger = {}
    with gzip.open(ledger_path, "rt", encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData":
                ledger[row["exportRelativePath"]] = row
    if not ledger:
        raise ValueError(f"{LABEL}.source:missing-ledger")
    for path, digest, start, end, span_digest in data["sourceReceipts"]:
        if not path.startswith("LevelScriptData/"):
            raise ValueError(f"{LABEL}.source:path={path}")
        payload = (export_root / path).read_bytes()
        if (
            not 0 <= start < end <= len(payload)
            or payload[start:start+4] != b"\xfa\xfa\x04\x0a"
            or _sha(payload) != digest.upper()
            or _sha(payload[start:end]) != span_digest.upper()
            or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
            or ledger.get(path, {}).get("length") != len(payload)
        ):
            raise ValueError(f"{LABEL}.source:receipt={path}@{start}")
        decoded, cursor = decode_typhoea_chip_id_action(payload, start, data["route"])
        if cursor != end or decoded["endOffset"] != end:
            raise ValueError(f"{LABEL}.source:cursor={path}@{start}")
    return len(data["sourceReceipts"])


def validate_typhoea_chip_id_native_contract(
    *, contract_path: Path = CONTRACT_PATH, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Fail closed on selected native and optional current-source drift."""
    try:
        data = _contract(Path(contract_path))
        expected = data["nativeInputs"]
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
        _validate_native(image, data)
        checked = 0
        if export_root is not None:
            if ledger_path is None or summary_path is None:
                raise ValueError(f"{LABEL}.source:explicit-summary-and-ledger-required")
            checked = _validate_sources(data, Path(export_root), Path(ledger_path), Path(summary_path))
        route = data["route"]
        return {"status": "validated", "evidenceBoundary": "exact",
                "route": {"family": route["family"], "tag": route["tag"],
                          "wrapperName": route["wrapperName"],
                          "fields": [field[:2] for field in route["fields"]]},
                "sourceReceiptsChecked": checked}
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as exc:
        failure = str(exc)
        check = (failure.split(".contract:", 1)[1] if ".contract:" in failure
                 else failure.split(".native:", 1)[1] if ".native:" in failure
                 else failure.split(".source:", 1)[1] if ".source:" in failure
                 else "contract-native-or-source")
        return {"status": "validation_failed", "failedCheck": check, "detail": failure,
                "validationFailures": [{"gate": check, "actual": failure[:500]}]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--export-root", type=Path, help="current exported game/Json root")
    parser.add_argument("--ledger", type=Path, help="matching JsonData per-file JSONL.gz ledger")
    parser.add_argument("--summary", type=Path, help="matching JsonData corpus summary")
    args = parser.parse_args(argv)
    audit = validate_typhoea_chip_id_native_contract(
        game_root=args.game_root, export_root=args.export_root,
        ledger_path=args.ledger, summary_path=args.summary,
    )
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
