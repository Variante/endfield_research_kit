"""Authenticate SetEntitiesVisibility's selected ActionBase stored layout.

The contract proves the installed reader, its nested types, and current source
cursors. It does not establish that visibility changes occur at runtime.
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
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import (
    generic_type_carrier, method_spec_record, method_spec_usage_index,
    unresolved_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-entities-visibility-native-contract.v1"
LABEL = "levelscriptEntitiesVisibilityNative"
CONTRACT_PATH = CONTRACTS_DIR / "levelscript_entities_visibility_native.json"
LAYOUT_PATH = Path(__file__).parent / "codecs" / "levelscript" / "action_map_layouts.json"

_NATIVE_TO_CODEC = {
    "bool": "bool", "int": "int32", "string": "string",
    "Beyond.GEnums.ScopeName": "int32",
    "Beyond.Gameplay.Actions.Param`1<bool>": "Param<bool>",
    "Beyond.Gameplay.Actions.Param`1<System.Collections.Generic.List`1<Beyond.Gameplay.Core.EntityPtr>>": "Param<List<EntityPtr>>",
    "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.View.ModelVisibleType>": "Param<ModelVisibleType>",
}
_ELEMENTS = ["bool", "bool", "System.Collections.Generic.List`1<Beyond.Gameplay.Core.EntityPtr>",
             "Beyond.Gameplay.View.ModelVisibleType"]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _contract(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_bytes())
    route = data["route"]
    fields = route["fields"]
    reads = data["readOrder"]
    contexts = data["paramContexts"]
    enum = data["enum"]
    expected_own = ["isVisible", "resetVisible", "targetEntities", "visibleSource"]
    if (
        data.get("schema") != SCHEMA or data.get("status") != "exact-current-build"
        or data.get("evidenceBoundary") != "exact"
        or set(data.get("nativeInputs", {})) != {"GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll"}
        or route.get("family") != "ActionBase" or route.get("tag") != 0x0406
        or route.get("typeName") != "Beyond.Gameplay.Actions.SetEntitiesVisibility"
        or route.get("memberCount") != 12 or route.get("inheritedMemberCount") != 8
        or not isinstance(fields, list) or len(fields) != 12
        or any(not isinstance(row, list) or len(row) != 3 or
               row[1] != _NATIVE_TO_CODEC.get(row[2]) for row in fields)
        or [row[0] for row in fields[8:]] != expected_own
        or [row[1] for row in fields[8:]] != ["Param<bool>", "Param<bool>",
                                             "Param<List<EntityPtr>>", "Param<ModelVisibleType>"]
        or len(data["methods"]) != 2 or len(data["codeWindows"]) != 2
        or data["methods"][0][1] != route.get("wrapperName")
        or not data["methods"][1][1].startswith(route["wrapperName"] + "+")
        or [row[2] for row in data["methods"]] != ["Deserialize", "Deserialize"]
        or len(reads) != 12 or [row["memberIndex"] for row in reads] != list(range(12))
        or [(row["fieldName"], row["readKind"]) for row in reads]
           != [(name, kind) for name, kind, _native in fields]
        or set(data["readerHelpers"]) != {kind for _name, kind, _native in fields}
        or any(row["readTargetRva"] != data["readerHelpers"][row["readKind"]] for row in reads)
        or len(contexts) != 4 or [row["memberIndex"] for row in contexts] != list(range(8, 12))
        or [row["elementTypeName"] for row in contexts] != _ELEMENTS
        or enum.get("typeName") != "Beyond.Gameplay.View.ModelVisibleType"
        or enum.get("underlyingType") != "int"
        or not enum.get("members")
        or len({row["id"] for row in enum["members"]}) != len(enum["members"])
        or bytes.fromhex(data["memberCountInstruction"]["hex"])[-1] != 12
        or not data.get("sourceReceipts")
        or any(len(row) != 5 for row in data["sourceReceipts"])
        or len({(row[0], row[2]) for row in data["sourceReceipts"]}) != len(data["sourceReceipts"])
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    layouts = json.loads(LAYOUT_PATH.read_bytes())
    matches = [row for row in layouts.get("layouts", []) if
               (row.get("family"), row.get("tag")) == (route["family"], route["tag"])]
    layout = matches[0] if len(matches) == 1 else None
    cursor = layout.get("cursorEvidence") if layout else None
    if (
        layouts.get("schema") != "endfield.action-map-layouts.v3"
        or layout is None or layout.get("nativeGate") != "levelscript_entities_visibility_native"
        or layout.get("wrapperName") != route["wrapperName"]
        or layout.get("memberCount") != route["memberCount"]
        or layout.get("fields") != [[name, kind] for name, kind, _native in fields]
        or not isinstance(cursor, dict)
        or not any([cursor.get("source"), cursor.get("sourceSha256"),
                    cursor.get("unionOffset"), cursor.get("endOffset"),
                    cursor.get("spanSha256")] == receipt for receipt in data["sourceReceipts"])
    ):
        raise ValueError(f"{LABEL}.contract:reviewed-layout-join")
    return data


def _call_target(image: Any, site: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:call={site:#x}")
    return site + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_context(image: Any, row: dict[str, Any], expected_type: str) -> None:
    cell, usage = image.nested_usage_cell(row, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if index != row["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:method-spec-index={row['memberIndex']}")
    address = int(image.registration["methodSpecs"], 16) + index * 12
    spec = method_spec_record(
        image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source=LABEL, offset=address,
    )
    method = image.metadata.methods[spec[0]]
    if (
        list(spec) != row["methodSpec"]
        or image.type_name(method.declaring_type) != "MemoryPack.MemoryPackReader"
        or image.metadata.string(method.name_index) != "ReadValue"
        or row["readerMethod"] != ["MemoryPack.MemoryPackReader", "ReadValue"]
    ):
        raise ValueError(f"{LABEL}.native:read-value-spec={row['memberIndex']}")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:read-value-arity={row['memberIndex']}")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != row["argumentRawHex"].upper() or raw[10] != row["typeKind"] or raw[10] != 0x15:
        raise ValueError(f"{LABEL}.native:param-type={row['memberIndex']}")
    carrier_pointer = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(carrier_pointer, 32)
    base_pointer = struct.unpack_from("<Q", carrier_raw)[0]
    base_raw = image.pe.bytes_at_va(base_pointer, 16)
    carrier = generic_type_carrier(
        raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
        type_count=len(image.metadata.types), source=LABEL,
    )
    if (carrier != row["classCarrier"]
            or image.type_name(carrier["baseDefinitionIndex"]) != "Beyond.Gameplay.Actions.Param`1"):
        raise ValueError(f"{LABEL}.native:param-carrier={row['memberIndex']}")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    if len(child.arguments) != 1 or child_row != row["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:param-instantiation={row['memberIndex']}")
    element = child.arguments[0]
    raw_element = bytes.fromhex(element.raw_type_record_hex)
    actual_type = il2cpp.runtime_type_name(image.pe, image.metadata, element.type_pointer_va)
    if (
        actual_type != expected_type or row["elementTypeName"] != expected_type
        or raw_element.hex().upper() != row["elementRawHex"].upper()
        or raw_element[10] != row["elementTypeKind"]
    ):
        raise ValueError(f"{LABEL}.native:param-element={row['memberIndex']}")
    if row["memberIndex"] == 10 and raw_element[10] != 0x15:
        raise ValueError(f"{LABEL}.native:list-type")
    if row["memberIndex"] == 11 and raw_element[10] != 0x11:
        raise ValueError(f"{LABEL}.native:enum-type")


def _validate_native(image: Any, data: dict[str, Any]) -> None:
    route = data["route"]
    dispatch = data["dispatcher"]
    base = image.pe.image_base
    wrappers = derive_from_image(image)
    switch = read_union_switch(image, "Beyond_Gameplay_Actions_ActionBaseForMemoryPack", wrappers=wrappers)
    entry = switch["entries"][route["tag"]]
    table_va = int(switch["tableVa"], 16)
    if (
        switch["entryCount"] != dispatch["switchEntryCount"]
        or table_va != base + dispatch["switchTableRva"]
        or _sha(image.pe.bytes_at_va(table_va, switch["entryCount"] * 4)) != dispatch["switchTableSha256"].upper()
        or int(entry["targetVa"], 16) != base + dispatch["switchTargetRva"]
        or int(entry["bodyVa"], 16) != base + dispatch["bodyRva"]
        or int(entry["usageCellVa"], 16) != base + dispatch["usageCellRva"]
        or entry["typeDefinition"] != route["typeDefinition"]
        or entry["registeredTypeIndex"] != route["registeredTypeIndex"]
        or entry["wrapperName"] != route["wrapperName"]
    ):
        raise ValueError(f"{LABEL}.native:dispatch")
    jump = image.pe.bytes_at_va(base + dispatch["switchTargetRva"], 5)
    if (
        jump[0] != 0xE9 or jump.hex().upper() != dispatch["switchEntryHex"].upper()
        or dispatch["switchTargetRva"] + 5 + struct.unpack_from("<i", jump, 1)[0] != dispatch["bodyRva"]
    ):
        raise ValueError(f"{LABEL}.native:switch-branch")
    image.check_windows([dispatch["branchWindow"]], label=LABEL)
    load = image.pe.bytes_at_va(base + dispatch["typeLoadRva"], 7)
    if load[:3] != b"\x48\x8b\x15" or load.hex().upper() != dispatch["typeLoadHex"].upper():
        raise ValueError(f"{LABEL}.native:type-load")
    usage_cell = base + dispatch["typeLoadRva"] + 7 + struct.unpack_from("<i", load, 3)[0]
    usage = image.pe.bytes_at_va(usage_cell, 8)
    index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1, source=LABEL, offset=usage_cell,
    )
    if (
        usage_cell != base + dispatch["usageCellRva"]
        or usage.hex().upper() != dispatch["usageRawHex"].upper()
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
        or len(wrapper.members) != route["memberCount"]
        or len(wrapper.inherited_members) != route["inheritedMemberCount"]
        or [[m.name.lstrip("_"), _NATIVE_TO_CODEC.get(m.declared_type), m.declared_type]
            for m in wrapper.members] != route["fields"]
        or any(m.kind != "enum" or m.underlying_kind != "scalar32" or m.width != 4
               for m in wrapper.members if m.declared_type == "Beyond.GEnums.ScopeName")
    ):
        raise ValueError(f"{LABEL}.native:wrapper-fields")
    methods = [image.validate_method_row(row, label=LABEL) for row in data["methods"]]
    image.check_windows(data["codeWindows"], label=LABEL)
    extents = image.mapper.pdata_function_extents(image.pe)
    for method_index, window in zip(methods, data["codeWindows"]):
        pointer = image.method_pointer_va(image.metadata.methods[method_index])
        if pointer - base != window["startRva"] or extents.get(pointer, 0)-base != window["endRva"]:
            raise ValueError(f"{LABEL}.native:method-extent")
    count = data["memberCountInstruction"]
    image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
    if not data["codeWindows"][0]["startRva"] < count["rva"] < data["codeWindows"][0]["endRva"]:
        raise ValueError(f"{LABEL}.native:member-count-range")
    previous = count["rva"]
    for read, member in zip(data["readOrder"], wrapper.members):
        if not previous < read["readCallRva"] < read["setterCallRva"] < data["codeWindows"][0]["endRva"]:
            raise ValueError(f"{LABEL}.native:read-order={read['memberIndex']}")
        if _call_target(image, read["readCallRva"], read["readCallHex"]) != read["readTargetRva"]:
            raise ValueError(f"{LABEL}.native:read-target={read['memberIndex']}")
        setter_method = image.metadata.methods[member.method_index]
        if (
            member.method_index != read["setterMethodIndex"]
            or image.method_pointer_va(setter_method)-base != read["setterTargetRva"]
            or _call_target(image, read["setterCallRva"], read["setterCallHex"]) != read["setterTargetRva"]
        ):
            raise ValueError(f"{LABEL}.native:setter={read['memberIndex']}")
        previous = read["setterCallRva"]
    for context in data["paramContexts"]:
        member = context["memberIndex"]
        read = data["readOrder"][member]
        if not data["readOrder"][member - 1]["setterCallRva"] < context["instructionRva"] < read["readCallRva"]:
            raise ValueError(f"{LABEL}.native:param-context-order={member}")
        _validate_context(image, context, _ELEMENTS[member - route["inheritedMemberCount"]])
    if len({data["readOrder"][r["memberIndex"]]["readTargetRva"] for r in data["paramContexts"]}) != 1:
        raise ValueError(f"{LABEL}.native:param-reader-target")
    enum = data["enum"]
    definition = enum["typeDefinition"]
    if image.type_name(definition) != enum["typeName"]:
        raise ValueError(f"{LABEL}.native:enum-definition")
    value_fields = [f for f in image.metadata.fields_for(image.metadata.types[definition])
                    if image.metadata.string(f.name_index) == "value__"]
    if len(value_fields) != 1:
        raise ValueError(f"{LABEL}.native:enum-width")
    table = int(image.registration["types"], 16)
    type_va = image.pe.u64_at_va(table + value_fields[0].type_index * 8)
    if il2cpp.runtime_type_name(image.pe, image.metadata, type_va) != enum["underlyingType"]:
        raise ValueError(f"{LABEL}.native:enum-width")
    members = il2cpp.native_enum_members(image.metadata, BodyIndex(image).enum_defaults,
                                          image.pe, image.registration, enum["typeName"])
    if [{"name": row["name"], "id": row["id"]} for row in members] != enum["members"]:
        raise ValueError(f"{LABEL}.native:enum-members")


def _validate_sources(data: dict[str, Any], export_root: Path, ledger_path: Path,
                      summary_path: Path) -> None:
    from scripts.game_data.codecs.levelscript.visibility_action import decode_visibility_action

    summary = json.loads(summary_path.read_bytes())
    if (
        summary.get("status") != "complete"
        or _sha(ledger_path.read_bytes())
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
        raise ValueError(f"{LABEL}.source:missing-ledger")
    enum_values = {row["id"]: row["name"] for row in data["enum"]["members"]}
    for path, digest, start, end, span_digest in data["sourceReceipts"]:
        if not path.startswith("LevelScriptData/"):
            raise ValueError(f"{LABEL}.source:path={path}")
        payload = (export_root / path).read_bytes()
        if (
            not 0 <= start < end <= len(payload)
            or _sha(payload) != digest.upper()
            or _sha(payload[start:end]) != span_digest.upper()
            or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
            or ledger.get(path, {}).get("length") != len(payload)
        ):
            raise ValueError(f"{LABEL}.source:receipt={path}@{start}")
        decoded, cursor = decode_visibility_action(payload, start, data["route"], enum_values)
        if cursor != end or decoded["endOffset"] != end:
            raise ValueError(f"{LABEL}.source:cursor={path}@{start}")


def validate_entities_visibility_native_contract(
    *, contract_path: Path = CONTRACT_PATH, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Fail closed on selected build, native body, and optional source drift."""
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
            return {"status": gate.status, "failedCheck": "installed-native-inputs",
                    "detail": gate.detail}
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        if not unity.is_file():
            return {"status": "missing", "failedCheck": "UnityPlayer.dll",
                    "detail": "selected UnityPlayer.dll is absent"}
        if sha256_file(unity).upper() != expected["UnityPlayer.dll"].upper():
            return {"status": "mismatched", "failedCheck": "UnityPlayer.dll",
                    "detail": "selected UnityPlayer.dll hash differs"}
        image = open_native_image(gate.gameassembly, gate.metadata)
        _validate_native(image, data)
        if export_root is not None:
            if ledger_path is None or summary_path is None:
                raise ValueError(f"{LABEL}.source:explicit-ledger-and-summary-required")
            _validate_sources(data, Path(export_root), Path(ledger_path), Path(summary_path))
        return {"status": "validated", "evidenceBoundary": "exact",
                "route": {"family": data["route"]["family"], "tag": data["route"]["tag"],
                          "wrapperName": data["route"]["wrapperName"],
                          "fields": [[name, kind] for name, kind, _native in data["route"]["fields"]]},
                "enumMembers": [[row["name"], row["id"]] for row in data["enum"]["members"]],
                "sourceReceiptsChecked": len(data["sourceReceipts"]) if export_root is not None else 0}
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as exc:
        detail = str(exc)
        check = (detail.split(f"{LABEL}.", 1)[1].split(":", 1)[0]
                 if detail.startswith(f"{LABEL}.") else "contract-native-or-source")
        return {"status": "validation_failed", "failedCheck": check,
                "detail": detail, "validationFailures": [{"gate": check, "actual": detail[:500]}]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--export-root", type=Path, help="current exported game/Json root")
    parser.add_argument("--ledger", type=Path, help="current JsonData per-file JSONL.gz ledger")
    parser.add_argument("--summary", type=Path, help="matching JsonData corpus summary")
    args = parser.parse_args(argv)
    result = validate_entities_visibility_native_contract(
        game_root=args.game_root, export_root=args.export_root,
        ledger_path=args.ledger, summary_path=args.summary,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
