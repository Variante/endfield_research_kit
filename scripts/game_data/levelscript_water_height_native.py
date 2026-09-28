"""Authenticate the selected WaterVolumeInfiniteSetHeight stored action.

The reviewed contract pins ActionBase `WaterVolumeInfiniteSetHeight` (tag
0x0516 in the contract): the selected branch, the complete chained reader and
forwarding formatter, twelve ordered native reads and setters, and four
`Param<T>` contexts (`isFixedSpeed`, `isSmooth`, the water-volume pointer
`target`, and `value`). The command takes no options: it always replays the
source cursors against `export_full/game/Json` and the current JsonData
per-file ledger and summary under `reports/animestudio/`, prints the audit and
exits nonzero unless it validates. `validate_water_height_native_contract`
accepts explicit export-root, ledger and summary paths instead. It proves
stored water-height settings; runtime water state remains unobserved.

`isFixedSpeed` and `isSmooth` are `Param<bool>`, `value` is `Param<float>`,
and the current native reader resolves the `Param<WaterVolumePtr>` target to
a raw eight-byte ID record.
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
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.levelscript_two_routes_native import _validate_context
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-water-height-native-contract.v1"
LABEL = "levelscriptWaterHeightNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_water_height_native.json"


def _contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    route = contract.get("route", {})
    fields = route.get("fields", [])
    reads = route.get("readOrder", [])
    contexts = route.get("paramContexts", [])
    if (
        contract.get("schema") != SCHEMA or contract.get("status") != "exact-current-build"
        or contract.get("evidenceBoundary") != "exact"
        or route.get("family") != "ActionBase" or route.get("tag") != 0x0516
        or route.get("typeName") != "Beyond.Gameplay.Actions.WaterVolumeInfiniteSetHeight"
        or route.get("memberCount") != 12 or route.get("inheritedMemberCount") != 8
        or not isinstance(fields, list) or len(fields) != 12
        or [row[1] for row in fields] != ["bool", "int32", "bool", "string", "int32",
                                            "bool", "bool", "int32", "Param<bool>",
                                            "Param<bool>", "Param<WaterVolumePtr>", "Param<float>"]
        or any(not isinstance(row, list) or len(row) != 3 for row in fields)
        or [row.get("memberIndex") for row in reads] != list(range(12))
        or [(row.get("fieldName"), row.get("readKind")) for row in reads]
        != [(row[0], row[1]) for row in fields]
        or [row.get("memberIndex") for row in contexts] != [8, 9, 10, 11]
        or [row.get("elementTypeName") for row in contexts]
        != [{"bool":"System.Boolean", "float":"System.Single"}.get(
            fields[index][2].split("<", 1)[1][:-1],
            fields[index][2].split("<", 1)[1][:-1]) for index in (8, 9, 10, 11)]
        or len(route.get("methods", [])) != 2 or len(route.get("codeWindows", [])) < 3
        or route.get("formatterTailJump", {}).get("targetRva") != route["methods"][0][3]
        or len(route.get("sourceReceipts", [])) < 1
        or any(len(row) != 5 for row in route["sourceReceipts"])
        or len({(row[0], row[2]) for row in route["sourceReceipts"]}) != len(route["sourceReceipts"])
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def _call_target(image: Any, site: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:callsite={site:#x}")
    return site + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    base = image.pe.image_base
    route, dispatcher = contract["route"], contract["dispatcher"]
    wrappers = derive_from_image(image)
    switch = read_union_switch(
        image, "Beyond_Gameplay_Actions_ActionBaseForMemoryPack", wrappers=wrappers,
    )
    if (switch["entryCount"] != dispatcher["switchEntryCount"]
            or int(switch["tableVa"], 16) != base + dispatcher["switchTableRva"]):
        raise ValueError(f"{LABEL}.native:switch-shape")
    table = image.pe.bytes_at_va(base + dispatcher["switchTableRva"], switch["entryCount"] * 4)
    if hashlib.sha256(table).hexdigest().upper() != dispatcher["switchTableSha256"].upper():
        raise ValueError(f"{LABEL}.native:switch-hash")
    branch = route["dispatcher"]
    target = struct.unpack_from("<I", table, route["tag"] * 4)[0]
    jump = image.pe.bytes_at_va(base + target, 5)
    entry = switch["entries"][route["tag"]]
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
    image.check_windows([branch["branchWindow"]], label=LABEL)
    load = image.pe.bytes_at_va(base + branch["typeLoadRva"], 7)
    if load[:3] != b"\x48\x8B\x15" or load.hex().upper() != branch["typeLoadHex"].upper():
        raise ValueError(f"{LABEL}.native:type-load")
    cell = base + branch["typeLoadRva"] + 7 + struct.unpack_from("<i", load, 3)[0]
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
        raise ValueError(f"{LABEL}.native:registered-wrapper")
    wrapper = wrappers[definition]
    if (
        wrapper.wrapped_type != route["typeName"]
        or len(wrapper.inherited_members) != route["inheritedMemberCount"]
        or [[member.name.lstrip("_"), member.declared_type] for member in wrapper.members]
        != [[row[0], row[2]] for row in route["fields"]]
    ):
        raise ValueError(f"{LABEL}.native:wrapper-fields")
    ptr_wrapper = next((item for item in wrappers.values() if item.wrapped_type == "Beyond.Gameplay.Core.WaterVolumePtr"), None)
    if (ptr_wrapper is None or not ptr_wrapper.frames_as_raw_struct
            or [(member.name.lstrip("_"), member.declared_type, member.width)
                for member in ptr_wrapper.members] != [("id", "ulong", 8)]):
        raise ValueError(f"{LABEL}.native:water-volume-pointer-layout")
    methods = [image.validate_method_row(row, label=LABEL) for row in route["methods"]]
    windows = route["codeWindows"]
    image.check_windows(windows, label=LABEL)
    extents = image.mapper.pdata_function_extents(image.pe)
    source = image.method_pointer_va(image.metadata.methods[methods[0]])
    formatter = image.method_pointer_va(image.metadata.methods[methods[1]])
    expected_windows = [(source-base, extents[source]-base),
                        *((va-base, va+length-base) for va,length in BodyIndex(image).chained_fragments.get(source, ())),
                        (formatter-base, extents[formatter]-base)]
    if [(win["startRva"], win["endRva"]) for win in windows] != expected_windows:
        raise ValueError(f"{LABEL}.native:complete-method-windows")
    tail = route["formatterTailJump"]
    tail_code = image.pe.bytes_at_va(base + tail["instructionRva"], 5)
    if (
        not windows[-1]["startRva"] <= tail["instructionRva"] < windows[-1]["endRva"]
        or tail_code[0] != 0xE9 or tail_code.hex().upper() != tail["instructionHex"].upper()
        or tail["instructionRva"] + 5 + struct.unpack_from("<i", tail_code, 1)[0] != tail["targetRva"]
    ):
        raise ValueError(f"{LABEL}.native:formatter-forwarding")
    count = route["memberCountInstruction"]
    image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
    if count["hex"].upper() != "4080FE0C":
        raise ValueError(f"{LABEL}.native:member-count-check")
    ranges = [(win["startRva"], win["endRva"]) for win in windows[:-1]]
    previous = count["rva"]
    for read in route["readOrder"]:
        read_site, setter_site = read["readCallRva"], read["setterCallRva"]
        member = wrapper.members[read["memberIndex"]]
        method = image.metadata.methods[member.method_index]
        if (
            not previous < read_site < setter_site
            or not any(start <= read_site < setter_site < end for start,end in ranges)
            or _call_target(image, read_site, read["readCallHex"]) != read["readTargetRva"]
            or _call_target(image, setter_site, read["setterCallHex"]) != read["setterTargetRva"]
            or member.method_index != read["setterMethodIndex"]
            or member.declaring_wrapper != read["declaringWrapper"]
            or image.metadata.string(method.name_index) != f"set___{member.name}__"
            or image.method_pointer_va(method) != base + read["setterTargetRva"]
        ):
            raise ValueError(f"{LABEL}.native:ordered-read-setter={read['memberIndex']}")
        previous = setter_site
    for context in route["paramContexts"]:
        member_index = context["memberIndex"]
        if not route["readOrder"][member_index-1]["setterCallRva"] < context["instructionRva"] < route["readOrder"][member_index]["readCallRva"]:
            raise ValueError(f"{LABEL}.native:param-context-order={member_index}")
        method = image.metadata.methods[context["methodSpec"][0]]
        if (image.type_name(method.declaring_type) != "MemoryPack.MemoryPackReader"
                or image.metadata.string(method.name_index) != "ReadValue"):
            raise ValueError(f"{LABEL}.native:param-reader-method={member_index}")
        _validate_context(image, context, context["elementTypeName"])


def _validate_sources(contract: dict[str, Any], export_root: Path, ledger_path: Path,
                      summary_path: Path) -> int:
    summary = json.loads(summary_path.read_bytes())
    if (summary.get("status") != "complete"
            or hashlib.sha256(ledger_path.read_bytes()).hexdigest().upper()
            != summary.get("provenance", {}).get("outputFiles", {}).get("sha256", "").upper()):
        raise ValueError(f"{LABEL}.source:summary-ledger-join")
    ledger = {}
    with gzip.open(ledger_path, "rt", encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData":
                ledger[row["exportRelativePath"]] = row
    route = contract["route"]
    prefix = b"\xfa\x16\x05\x0c"
    for path,digest,start,end,span_digest in route["sourceReceipts"]:
        data = (export_root / path).read_bytes()
        if (
            not 0 <= start < end <= len(data) or data[start:start+4] != prefix
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
            or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
            or ledger.get(path, {}).get("length") != len(data)
        ):
            raise ValueError(f"{LABEL}.source:receipt={path},offset={start}")
    return len(route["sourceReceipts"])


def validate_water_height_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Return no route when native inputs, selected body, or source receipts drift."""
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
            return {"status":"validation_failed","failedCheck":"installed-native-inputs",
                    "nativeStatus":gate.status,"detail":gate.detail,
                    "validationFailures":[{"gate":"installed_native_inputs"}]}
        unity=gate.gameassembly.parent/"UnityPlayer.dll"
        if not unity.is_file() or sha256_file(unity).upper()!=expected["UnityPlayer.dll"].upper():
            raise ValueError(f"{LABEL}.native:UnityPlayer.dll")
        image=open_native_image(gate.gameassembly,gate.metadata)
        _validate_native(image,contract)
        checked=0
        if export_root is not None:
            if ledger_path is None or summary_path is None:
                raise ValueError(f"{LABEL}.source:explicit-summary-and-ledger-required")
            checked=_validate_sources(contract,Path(export_root),Path(ledger_path),Path(summary_path))
        route=contract["route"]
        return {"status":"validated","evidenceBoundary":"exact",
                "route":{"family":route["family"],"tag":route["tag"],
                         "wrapperName":route["wrapperName"],
                         "fields":[field[:2] for field in route["fields"]]},
                "sourceReceiptsChecked":checked}
    except (KeyError,IndexError,TypeError,ValueError,OSError,RuntimeError) as exc:
        return {"status":"validation_failed","failedCheck":"selected-route-contract-native-or-source",
                "detail":str(exc),"validationFailures":[{"gate":"selected_route_contract_native_or_source"}]}


def main() -> int:
    audit=validate_water_height_native_contract(
        export_root=Path("export_full/game/Json"),
        ledger_path=Path("reports/animestudio/jsondata_current_files_latest.jsonl.gz"),
        summary_path=Path("reports/animestudio/jsondata_current_latest.json"),
    )
    print(json.dumps(audit,indent=2))
    return 0 if audit["status"]=="validated" else 1


if __name__=="__main__":
    raise SystemExit(main())
