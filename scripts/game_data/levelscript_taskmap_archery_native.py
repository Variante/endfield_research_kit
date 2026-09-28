"""Authenticate the selected CheckTyphoeaArcheryUnitsComplete reader.

The stored route is admitted only when the installed GameCondition branch,
complete native reader and formatter, nested generic contexts and source
spans still match the reviewed contract.
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


SCHEMA = "endfield.levelscript-taskmap-archery-native.v1"
LABEL = "levelscriptTaskMapArcheryNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_taskmap_archery_native.json"
_DECLARED_KIND = {
    "Beyond.GEnums.ScopeName": "enum32",
    "string": "string",
    "bool": "bool",
    "Beyond.Gameplay.Actions.Param`1<string>": "Param<string>",
    "Beyond.Gameplay.Actions.Param`1<System.Collections.Generic.List`1<Beyond.Gameplay.Core.LsmPtr>>": "Param<List<LsmPtr>>",
    "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.LevelScriptPtr>": "Param<LevelScriptPtr>",
}
_PARAM_TYPES = ("System.String", "System.Collections.Generic.List`1", "Beyond.Gameplay.Core.LevelScriptPtr")


def _contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    route = contract.get("route") or {}
    fields = route.get("fields") or []
    native = route.get("nativeDeclaredTypes") or []
    reads = route.get("orderedReads") or []
    contexts = route.get("paramContexts") or []
    methods = route.get("methods") or []
    windows = route.get("codeWindows") or []
    receipts = route.get("sourceReceipts") or []
    if (
        contract.get("schema") != SCHEMA or contract.get("status") != "exact-current-build"
        or set(contract.get("nativeInputs") or {})
        != {"GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll"}
        or route.get("family") != "GameCondition"
        or route.get("typeName") != "Beyond.Gameplay.CheckTyphoeaArcheryUnitsComplete"
        or route.get("serializedMemberCount") != len(fields) or len(fields) != 7
        or route.get("inheritedMemberCount") != 4
        or len(native) != len(fields)
        or [[row[0], _DECLARED_KIND.get(row[1])] for row in native] != fields
        or fields[:4] != [["scopeMask", "enum32"], ["uniqueId", "string"],
                          ["useCurrentScope", "bool"], ["useGraphScope", "bool"]]
        or [row[1] for row in fields[4:]] != ["Param<string>", "Param<List<LsmPtr>>", "Param<LevelScriptPtr>"]
        or [row.get("memberIndex") for row in reads] != list(range(7))
        or [[row.get("fieldName"),row.get("readKind")] for row in reads] != fields
        or [row.get("memberIndex") for row in contexts] != [4,5,6]
        or [row.get("elementTypeName") for row in contexts] != list(_PARAM_TYPES)
        or contexts[1].get("nestedList", {}).get("elementTypeName") != "Beyond.Gameplay.Core.LsmPtr"
        or len(methods) != 2 or len(windows) != 2
        or methods[0][1] != route["wrapperName"]
        or not methods[1][1].startswith(route["wrapperName"] + "+")
        or [row[2] for row in methods] != ["Deserialize", "Deserialize"]
        or route.get("formatterTailJump", {}).get("targetRva") != methods[0][3]
        or any(len(row) != 5 for row in receipts)
        or len({(row[0],row[2]) for row in receipts}) != len(receipts)
        or (contract.get("pointers") or {}).get("LsmPtr", {}).get("fields") != [["id", "ulong"]]
        or (contract.get("pointers") or {}).get("LevelScriptPtr", {}).get("fields") != [["scriptId", "ulong"]]
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
    index = method_spec_usage_index(usage, image.registration["methodSpecsCount"],
                                    source=LABEL, offset=cell)
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:context-spec-index")
    address = int(image.registration["methodSpecs"], 16) + index * 12
    spec = method_spec_record(image.pe.bytes_at_va(address, 12),
                              len(image.metadata.methods), image.registration["genericInstsCount"],
                              source=LABEL, offset=address)
    method = image.metadata.methods[spec[0]]
    if (list(spec) != context["methodSpec"]
            or image.type_name(method.declaring_type) != "MemoryPack.MemoryPackReader"
            or image.metadata.string(method.name_index) != "ReadValue"):
        raise ValueError(f"{LABEL}.native:context-reader")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:context-argument-count")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"] or raw[10] != 0x15:
        raise ValueError(f"{LABEL}.native:context-param")
    pointer = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(pointer, 32)
    base_ptr = struct.unpack_from("<Q", carrier_raw)[0]
    base_raw = image.pe.bytes_at_va(base_ptr, 16)
    carrier = generic_type_carrier(raw, carrier_raw, base_raw,
                                   type_pointer=argument.type_pointer_va,
                                   type_count=len(image.metadata.types), source=LABEL)
    if (carrier != context["classCarrier"]
            or image.type_name(carrier["baseDefinitionIndex"])
            != "Beyond.Gameplay.Actions.Param`1"):
        raise ValueError(f"{LABEL}.native:context-carrier")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    if len(child.arguments) != 1 or child_row != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:context-instantiation")
    child_argument = child.arguments[0]
    element = bytes.fromhex(child_argument.raw_type_record_hex)
    nested = context.get("nestedList")
    if element[10] == 0x15:
        if not isinstance(nested, dict):
            raise ValueError(f"{LABEL}.native:missing-nested-list")
        list_pointer = struct.unpack_from("<Q", element)[0]
        list_carrier_raw = image.pe.bytes_at_va(list_pointer, 32)
        list_base_pointer = struct.unpack_from("<Q", list_carrier_raw)[0]
        list_carrier = generic_type_carrier(
            element, list_carrier_raw, image.pe.bytes_at_va(list_base_pointer, 16),
            type_pointer=child_argument.type_pointer_va,
            type_count=len(image.metadata.types), source=LABEL,
        )
        definition = list_carrier["baseDefinitionIndex"]
        actual = image.type_name(definition)
        list_instance = image.instantiations.resolve_pointer(
            list_carrier["classInstantiationPointerVa"]
        )
        list_row = list_instance.as_dict()
        list_row["arguments"] = list(list_row["arguments"])
        if len(list_instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:list-argument-count")
        list_element = bytes.fromhex(list_instance.arguments[0].raw_type_record_hex)
        list_definition = struct.unpack_from("<Q", list_element)[0]
        if (
            list_carrier != nested.get("carrier")
            or list_row != nested.get("classInstantiation")
            or list_element[10] != 0x11
            or list_element.hex().upper() != nested.get("elementRawHex")
            or list_definition != nested.get("elementTypeDefinition")
            or image.type_name(list_definition) != nested.get("elementTypeName")
        ):
            raise ValueError(f"{LABEL}.native:nested-list-element")
    else:
        if nested is not None:
            raise ValueError(f"{LABEL}.native:unexpected-nested-list")
        definition = struct.unpack_from("<Q", element)[0] if element[10] in (0x11, 0x12) else None
        actual = image.type_name(definition) if definition is not None else {14: "System.String"}.get(element[10])
    if (
        element.hex().upper() != context["elementRawHex"]
        or element[10] != context["elementTypeKind"]
        or definition != context["elementTypeDefinition"]
        or actual != expected or context["elementTypeName"] != expected
    ):
        raise ValueError(f"{LABEL}.native:context-element={expected}")


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    base = image.pe.image_base
    dispatcher, route = contract["dispatcher"], contract["route"]
    wrappers = derive_from_image(image)
    switch = read_union_switch(image, "Beyond_Gameplay_GameConditionForMemoryPack", wrappers=wrappers)
    if (switch["entryCount"] != dispatcher["entryCount"]
            or int(switch["tableVa"],16) != base + dispatcher["tableRva"]):
        raise ValueError(f"{LABEL}.native:dispatcher")
    table = image.pe.bytes_at_va(base + dispatcher["tableRva"], dispatcher["entryCount"]*4)
    if hashlib.sha256(table).hexdigest().upper() != dispatcher["tableSha256"].upper():
        raise ValueError(f"{LABEL}.native:switch-table")
    entry = switch["entries"][route["tag"]]
    wrapper = wrappers[route["typeDefinition"]]
    if (
        struct.unpack_from("<I",table,route["tag"]*4)[0] != route["switchTargetRva"]
        or entry["wrapperName"] != route["wrapperName"]
        or entry["typeDefinition"] != route["typeDefinition"]
        or entry["registeredTypeIndex"] != route["registeredTypeIndex"]
        or int(entry["targetVa"],16) != base + route["switchTargetRva"]
        or int(entry["bodyVa"],16) != base + route["bodyRva"]
        or int(entry["usageCellVa"],16) != base + route["usageCellRva"]
        or image.pe.bytes_at_va(base + route["usageCellRva"],8).hex().upper()
        != route["usageRawHex"].upper()
        or wrapper.wrapped_type != route["typeName"]
        or len(wrapper.inherited_members) != route["inheritedMemberCount"]
        or [[member.name.lstrip("_"),member.declared_type] for member in wrapper.members]
        != route["nativeDeclaredTypes"]
    ):
        raise ValueError(f"{LABEL}.native:selected-wrapper")
    for name, pointer in contract["pointers"].items():
        actual = wrappers.get(pointer["typeDefinition"])
        if (actual is None or actual.name != pointer["wrapperName"]
                or actual.wrapped_type != pointer["wrappedType"]
                or actual.wrapped_type != "Beyond.Gameplay.Core." + name
                or [[m.name,m.declared_type] for m in actual.members] != pointer["fields"]):
            raise ValueError(f"{LABEL}.native:{name}-layout")
    methods = [image.validate_method_row(row,label=LABEL) for row in route["methods"]]
    source = image.method_pointer_va(image.metadata.methods[methods[0]])
    formatter = image.method_pointer_va(image.metadata.methods[methods[1]])
    extents = image.mapper.pdata_function_extents(image.pe)
    expected = [(source-base,extents[source]-base),
                *((va-base,va+size-base) for va,size in BodyIndex(image).chained_fragments.get(source, ())),
                (formatter-base,extents[formatter]-base)]
    windows = route["codeWindows"]
    if [(w["startRva"],w["endRva"]) for w in windows] != expected:
        raise ValueError(f"{LABEL}.native:complete-method-windows")
    image.check_windows(windows,label=LABEL)
    tail = route["formatterTailJump"]
    code = image.pe.bytes_at_va(base+tail["instructionRva"],5)
    if (not windows[-1]["startRva"] <= tail["instructionRva"] < windows[-1]["endRva"]
            or code[0] != 0xE9 or code.hex().upper() != tail["instructionHex"].upper()
            or tail["instructionRva"]+5+struct.unpack_from("<i",code,1)[0] != source-base):
        raise ValueError(f"{LABEL}.native:formatter-forwarding")
    count = route["memberCountInstruction"]
    image.check_instruction_windows([[count["rva"],count["hex"]]],label=LABEL)
    main_start,main_end = windows[0]["startRva"],windows[0]["endRva"]
    count_raw = bytes.fromhex(count["hex"])
    if (
        not main_start <= count["rva"] < route["orderedReads"][0]["readCallRva"]
        or len(count_raw) != 5 or count_raw[:3] != b"\x80\x7c\x24"
        or count_raw[-1] != route["serializedMemberCount"]
    ):
        raise ValueError(f"{LABEL}.native:member-count-position")
    previous = count["rva"]
    for read in route["orderedReads"]:
        read_site,setter_site = read["readCallRva"],read["setterCallRva"]
        member = wrapper.members[read["memberIndex"]]
        method = image.metadata.methods[member.method_index]
        if (
            not previous < read_site < setter_site < main_end
            or _call_target(image,read_site,read["readCallHex"]) != read["readTargetRva"]
            or _call_target(image,setter_site,read["setterCallHex"]) != read["setterTargetRva"]
            or member.method_index != read["setterMethodIndex"]
            or member.declaring_wrapper != read["declaringWrapper"]
            or image.metadata.string(method.name_index) != f"set___{member.name}__"
            or image.method_pointer_va(method) != base+read["setterTargetRva"]
        ):
            raise ValueError(f"{LABEL}.native:ordered-read-setter={read['memberIndex']}")
        previous = setter_site
    for context in route["paramContexts"]:
        index = context["memberIndex"]
        if not (route["orderedReads"][index-1]["setterCallRva"]
                < context["instructionRva"] < route["orderedReads"][index]["readCallRva"]):
            raise ValueError(f"{LABEL}.native:context-order={index}")
        _validate_context(image,context,_PARAM_TYPES[index-4])


def _validate_sources(contract: dict[str, Any], export_root: Path,
                      ledger_path: Path, summary_path: Path) -> int:
    summary = json.loads(summary_path.read_bytes())
    if (summary.get("status") != "complete"
            or hashlib.sha256(ledger_path.read_bytes()).hexdigest().upper()
            != summary.get("provenance",{}).get("outputFiles",{}).get("sha256","").upper()):
        raise ValueError(f"{LABEL}.source:summary-ledger-join")
    ledger = {}
    with gzip.open(ledger_path,"rt",encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData":
                ledger[row["exportRelativePath"]] = row
    route = contract["route"]
    tag = route["tag"]
    prefix = (bytes((tag,)) if tag < 0xFA else b"\xfa" + tag.to_bytes(2, "little"))
    prefix += bytes((route["serializedMemberCount"],))
    receipts = route["sourceReceipts"]
    if not receipts:
        raise ValueError(f"{LABEL}.source:no-receipts")
    for path,digest,start,end,span_digest in receipts:
        data = (export_root/path).read_bytes()
        if (
            not 0 <= start < end <= len(data)
            or data[start:start+len(prefix)] != prefix
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
            or ledger.get(path,{}).get("logicalSha256","").upper() != digest.upper()
            or ledger.get(path,{}).get("length") != len(data)
        ):
            raise ValueError(f"{LABEL}.source:receipt={path}@{start}")
    return len(receipts)


@lru_cache(maxsize=4)
def validate_levelscript_taskmap_archery_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Return a route only after native and requested source evidence validates."""
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
            return {"status":gate.status,"failedGate":"installed_native_inputs",
                    "detail":gate.detail,"routeCount":0}
        unity = gate.gameassembly.parent/"UnityPlayer.dll"
        if not unity.is_file() or sha256_file(unity).upper() != expected["UnityPlayer.dll"].upper():
            raise ValueError(f"{LABEL}.native:UnityPlayer.dll")
        _validate_native(open_native_image(gate.gameassembly,gate.metadata),contract)
        count = 0
        if any(value is not None for value in (export_root,ledger_path,summary_path)):
            if not all(value is not None for value in (export_root,ledger_path,summary_path)):
                raise ValueError(f"{LABEL}.source:incomplete-paths")
            count = _validate_sources(contract,Path(export_root),Path(ledger_path),Path(summary_path))
        return {"status":"validated","evidenceBoundary":"exact","routeCount":1,
                "sourceReceiptCount":count}
    except (OSError,ValueError,KeyError,TypeError,IndexError) as error:
        return {"status":"validation_failed","failedGate":str(error).split(":",1)[0],
                "detail":str(error)[:400],"routeCount":0}


@lru_cache(maxsize=1)
def validated_taskmap_archery_route() -> dict[str, Any] | None:
    if validate_levelscript_taskmap_archery_native_contract()["status"] != "validated":
        return None
    return _contract(DEFAULT_CONTRACT)["route"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root",type=Path)
    parser.add_argument("--contract",type=Path,default=DEFAULT_CONTRACT)
    parser.add_argument("--export-root",type=Path)
    parser.add_argument("--ledger",type=Path)
    parser.add_argument("--summary",type=Path)
    args = parser.parse_args(argv)
    result = validate_levelscript_taskmap_archery_native_contract(
        contract_path=args.contract,game_root=args.game_root,export_root=args.export_root,
        ledger_path=args.ledger,summary_path=args.summary)
    print(json.dumps(result,indent=2))
    return 0 if result["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
