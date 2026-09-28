"""Authenticate the selected CheckGameInstStartDuration task condition.

The reviewed contract pins GameCondition `CheckGameInstStartDuration` (at
the contract's tag): the selected switch branch, generated wrapper and
LevelScriptPtr, the complete reader and forwarding formatter, nine ordered
parameter reads and setters, and five generic `Param` contexts. Passing
`--export-root`, `--ledger` and `--summary` together also replays the
reviewed source cursors against the current JsonData ledger. The command
prints its audit and exits nonzero unless it validates. It proves the stored
condition shape; duration evaluation and condition truth remain unobserved.

After the four inherited condition fields the condition stores
`Param<CompareOperator>`, `Param<int>`, the level as `Param<string>`, the
script as `Param<LevelScriptPtr>` and the sub-game as `Param<string>`.
`codecs.levelscript.taskmap_game_inst_duration_condition` reads it inside
positive task maps; the reached dungeon owners then advance through their
task maps and final trigger volumes to physical EOF.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import generic_type_carrier, method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-check-game-inst-start-duration-native.v1"
LABEL = "levelscriptCheckGameInstStartDurationNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_check_game_inst_start_duration_native.json"
_DECLARED_KIND = {
    "Beyond.GEnums.ScopeName": "enum32", "string": "string", "bool": "bool",
    "Beyond.Gameplay.Actions.Param`1<Beyond.GEnums.CompareOperator>": "Param<CompareOperator>",
    "Beyond.Gameplay.Actions.Param`1<int>": "Param<int>",
    "Beyond.Gameplay.Actions.Param`1<string>": "Param<string>",
    "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.LevelScriptPtr>": "Param<LevelScriptPtr>",
}
_PARAM_TYPES = {
    "Param<CompareOperator>": "Beyond.GEnums.CompareOperator",
    "Param<int>": "System.Int32",
    "Param<string>": "System.String",
    "Param<LevelScriptPtr>": "Beyond.Gameplay.Core.LevelScriptPtr",
}
_PRIMITIVE_TYPES = {2: "System.Boolean", 8: "System.Int32", 14: "System.String"}


def _contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    route = contract.get("route") or {}
    fields = route.get("fields") or []
    native = route.get("nativeDeclaredTypes") or []
    reads = route.get("orderedReads") or []
    contexts = route.get("paramContexts") or []
    methods = route.get("methods") or []
    receipts = route.get("sourceReceipts") or []
    if (
        contract.get("schema") != SCHEMA or contract.get("status") != "exact-current-build"
        or set(contract.get("nativeInputs") or {})
        != {"GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll"}
        or route.get("family") != "GameCondition"
        or route.get("typeName") != "Beyond.Gameplay.CheckGameInstStartDuration"
        or route.get("serializedMemberCount") != len(fields) or len(fields) != 9
        or route.get("inheritedMemberCount") != 4
        or [[name, _DECLARED_KIND.get(kind)] for name, kind in native] != fields
        or fields != [
            ["scopeMask", "enum32"], ["uniqueId", "string"],
            ["useCurrentScope", "bool"], ["useGraphScope", "bool"],
            ["compareOperator", "Param<CompareOperator>"],
            ["progressToCompare", "Param<int>"], ["levelId", "Param<string>"],
            ["scriptId", "Param<LevelScriptPtr>"], ["subGameId", "Param<string>"],
        ]
        or [row.get("memberIndex") for row in reads] != list(range(9))
        or [row.get("fieldName") for row in reads] != [row[0] for row in fields]
        or [row.get("readKind") for row in reads] != [
            "generic" if kind in _PARAM_TYPES else kind for _, kind in fields
        ]
        or [row.get("memberIndex") for row in contexts] != list(range(4, 9))
        or [row.get("fieldName") for row in contexts] != [row[0] for row in fields[4:]]
        or len(methods) != 2 or len(route.get("codeWindows") or []) != 2
        or methods[0][1] != route.get("wrapperName")
        or not methods[1][1].startswith(route["wrapperName"] + "+")
        or [row[2] for row in methods] != ["Deserialize", "Deserialize"]
        or route.get("formatterTailJump", {}).get("targetRva") != methods[0][3]
        or not receipts or any(len(row) != 5 for row in receipts)
        or len({(row[0], row[2]) for row in receipts}) != len(receipts)
        or (contract.get("pointers") or {}).get("LevelScriptPtr", {}).get("fields")
        != [["scriptId", "ulong"]]
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def _call_target(image: Any, site: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:callsite={site:#x}")
    return site + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_context(image: Any, context: dict[str, Any], expected: str) -> None:
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:context-spec-index")
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
        raise ValueError(f"{LABEL}.native:context-reader")
    inst = image.instantiations.resolve(spec[2])
    if len(inst.arguments) != 1:
        raise ValueError(f"{LABEL}.native:context-argument-count")
    arg = inst.arguments[0]
    raw = bytes.fromhex(arg.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"] or raw[10] != 0x15:
        raise ValueError(f"{LABEL}.native:context-argument")
    pointer = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(pointer, 32)
    base_pointer = struct.unpack_from("<Q", carrier_raw)[0]
    carrier = generic_type_carrier(
        raw, carrier_raw, image.pe.bytes_at_va(base_pointer, 16),
        type_pointer=arg.type_pointer_va, type_count=len(image.metadata.types), source=LABEL,
    )
    if (
        carrier != context["classCarrier"]
        or image.type_name(carrier["baseDefinitionIndex"])
        != "Beyond.Gameplay.Actions.Param`1"
    ):
        raise ValueError(f"{LABEL}.native:context-param")
    child_inst = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    row = child_inst.as_dict()
    row["arguments"] = list(row["arguments"])
    if len(child_inst.arguments) != 1 or row != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:context-instantiation")
    child_raw = bytes.fromhex(child_inst.arguments[0].raw_type_record_hex)
    reviewed = context["child"]
    if (
        child_raw.hex().upper() != reviewed["rawHex"]
        or child_raw[10] != reviewed["kind"]
    ):
        raise ValueError(f"{LABEL}.native:context-child-raw")
    if child_raw[10] in (0x11, 0x12):
        definition = struct.unpack_from("<Q", child_raw)[0]
        actual = image.type_name(definition)
        if definition != reviewed.get("typeDefinition"):
            raise ValueError(f"{LABEL}.native:context-child-definition")
    else:
        actual = _PRIMITIVE_TYPES.get(child_raw[10])
    if actual != expected or reviewed.get("typeName") != expected:
        raise ValueError(f"{LABEL}.native:context-child-type={expected}")


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    base = image.pe.image_base
    dispatcher, route = contract["dispatcher"], contract["route"]
    wrappers = derive_from_image(image)
    switch = read_union_switch(image, "Beyond_Gameplay_GameConditionForMemoryPack", wrappers=wrappers)
    if (
        switch["entryCount"] != dispatcher["entryCount"]
        or int(switch["tableVa"], 16) != base + dispatcher["tableRva"]
    ):
        raise ValueError(f"{LABEL}.native:dispatcher")
    table = image.pe.bytes_at_va(base + dispatcher["tableRva"], dispatcher["entryCount"] * 4)
    if hashlib.sha256(table).hexdigest().upper() != dispatcher["tableSha256"].upper():
        raise ValueError(f"{LABEL}.native:switch-table")
    entry = switch["entries"][route["tag"]]
    wrapper = wrappers[route["typeDefinition"]]
    if (
        struct.unpack_from("<I", table, route["tag"] * 4)[0] != route["switchTargetRva"]
        or entry["wrapperName"] != route["wrapperName"]
        or entry["typeDefinition"] != route["typeDefinition"]
        or entry["registeredTypeIndex"] != route["registeredTypeIndex"]
        or int(entry["targetVa"], 16) != base + route["switchTargetRva"]
        or int(entry["bodyVa"], 16) != base + route["bodyRva"]
        or int(entry["usageCellVa"], 16) != base + route["usageCellRva"]
        or image.pe.bytes_at_va(base + route["usageCellRva"], 8).hex().upper()
        != route["usageRawHex"].upper()
        or wrapper.wrapped_type != route["typeName"]
        or len(wrapper.inherited_members) != route["inheritedMemberCount"]
        or [[member.name.lstrip("_"), member.declared_type] for member in wrapper.members]
        != route["nativeDeclaredTypes"]
    ):
        raise ValueError(f"{LABEL}.native:selected-wrapper")
    pointer = contract["pointers"]["LevelScriptPtr"]
    actual = wrappers.get(pointer["typeDefinition"])
    if (
        actual is None or actual.name != pointer["wrapperName"]
        or actual.wrapped_type != pointer["wrappedType"]
        or actual.wrapped_type != "Beyond.Gameplay.Core.LevelScriptPtr"
        or [[member.name, member.declared_type] for member in actual.members]
        != pointer["fields"]
    ):
        raise ValueError(f"{LABEL}.native:LevelScriptPtr-layout")
    methods = [image.validate_method_row(row, label=LABEL) for row in route["methods"]]
    reader = image.method_pointer_va(image.metadata.methods[methods[0]])
    formatter = image.method_pointer_va(image.metadata.methods[methods[1]])
    extents = image.mapper.pdata_function_extents(image.pe)
    chained = BodyIndex(image).chained_fragments
    expected = [
        (reader - base, extents[reader] - base),
        *((va - base, va + size - base) for va, size in chained.get(reader, ())),
        (formatter - base, extents[formatter] - base),
    ]
    windows = route["codeWindows"]
    if [(window["startRva"], window["endRva"]) for window in windows] != expected:
        raise ValueError(f"{LABEL}.native:complete-method-windows")
    image.check_windows(windows, label=LABEL)
    tail = route["formatterTailJump"]
    code = image.pe.bytes_at_va(base + tail["instructionRva"], 5)
    if (
        not windows[-1]["startRva"] <= tail["instructionRva"] < windows[-1]["endRva"]
        or code[0] != 0xE9 or code.hex().upper() != tail["instructionHex"].upper()
        or tail["instructionRva"] + 5 + struct.unpack_from("<i", code, 1)[0] != reader - base
    ):
        raise ValueError(f"{LABEL}.native:formatter-forwarding")
    count = route["memberCountInstruction"]
    image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
    count_raw = bytes.fromhex(count["hex"])
    if (
        not windows[0]["startRva"] <= count["rva"] < route["orderedReads"][0]["readCallRva"]
        or len(count_raw) != 5 or count_raw[:4] != b"\x80\x7c\x24\x38"
        or count_raw[-1] != route["serializedMemberCount"]
    ):
        raise ValueError(f"{LABEL}.native:member-count")
    previous = count["rva"]
    for read in route["orderedReads"]:
        read_site, setter_site = read["readCallRva"], read["setterCallRva"]
        member = wrapper.members[read["memberIndex"]]
        setter = image.metadata.methods[member.method_index]
        if (
            not previous < read_site < setter_site < windows[0]["endRva"]
            or _call_target(image, read_site, read["readCallHex"]) != read["readTargetRva"]
            or _call_target(image, setter_site, read["setterCallHex"]) != read["setterTargetRva"]
            or member.method_index != read["setterMethodIndex"]
            or member.declaring_wrapper != read["declaringWrapper"]
            or image.metadata.string(setter.name_index) != f"set___{member.name}__"
            or image.method_pointer_va(setter) != base + read["setterTargetRva"]
        ):
            raise ValueError(f"{LABEL}.native:ordered-read-setter={read['memberIndex']}")
        previous = setter_site
    for context in route["paramContexts"]:
        index = context["memberIndex"]
        read = route["orderedReads"][index]
        if (
            context["fieldName"] != read["fieldName"]
            or context["instructionRva"] != read["contextLoadRva"]
            or context["instructionHex"] != read["contextLoadHex"]
            or context["cellRva"] != read["contextCellRva"]
            or not route["orderedReads"][index - 1]["setterCallRva"]
            < context["instructionRva"] < read["readCallRva"]
        ):
            raise ValueError(f"{LABEL}.native:context-order={index}")
        _validate_context(image, context, _PARAM_TYPES[route["fields"][index][1]])


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
    ledger = {}
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData":
                ledger[row["exportRelativePath"]] = row
    from scripts.game_data.codecs.levelscript.taskmap_game_inst_duration_condition import (
        decode_game_inst_duration_condition,
    )
    route = contract["route"]
    prefix = bytes((route["tag"], route["serializedMemberCount"]))
    for path, digest, start, end, span_digest in route["sourceReceipts"]:
        data = (export_root / path).read_bytes()
        if (
            not 0 <= start < end <= len(data)
            or data[start:start + 2] != prefix
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
            or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
            or ledger.get(path, {}).get("length") != len(data)
        ):
            raise ValueError(f"{LABEL}.source:receipt={path}@{start}")
        decoded = decode_game_inst_duration_condition(data, start, len(data), route)
        if decoded is None or decoded[1] != end:
            raise ValueError(f"{LABEL}.source:cursor={path}@{start},expected={end}")
    return len(route["sourceReceipts"])


@lru_cache(maxsize=4)
def validate_levelscript_check_game_inst_start_duration_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Fail closed on installed build, complete native bodies, or source drift."""
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
            return {"status": gate.status, "failedGate": "installed_native_inputs",
                    "detail": gate.detail, "routeCount": 0}
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        if not unity.is_file() or sha256_file(unity).upper() != expected["UnityPlayer.dll"].upper():
            raise ValueError(f"{LABEL}.native:UnityPlayer.dll")
        _validate_native(open_native_image(gate.gameassembly, gate.metadata), contract)
        count = 0
        if any(value is not None for value in (export_root, ledger_path, summary_path)):
            if not all(value is not None for value in (export_root, ledger_path, summary_path)):
                raise ValueError(f"{LABEL}.source:incomplete-paths")
            count = _validate_sources(contract, Path(export_root), Path(ledger_path), Path(summary_path))
        return {"status": "validated", "evidenceBoundary": "exact", "routeCount": 1,
                "route": contract["route"], "sourceReceiptCount": count}
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        return {"status": "validation_failed", "failedGate": str(error).split(":", 1)[0],
                "detail": str(error)[:400], "routeCount": 0}


@lru_cache(maxsize=1)
def validated_check_game_inst_start_duration_route() -> dict[str, Any] | None:
    result = validate_levelscript_check_game_inst_start_duration_native_contract()
    return result.get("route") if result["status"] == "validated" else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)
    result = validate_levelscript_check_game_inst_start_duration_native_contract(
        contract_path=args.contract, game_root=args.game_root, export_root=args.export_root,
        ledger_path=args.ledger, summary_path=args.summary,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "route"}, indent=2))
    return 0 if result["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
