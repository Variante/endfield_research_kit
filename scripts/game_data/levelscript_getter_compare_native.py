"""Authenticate selected CompareMissionState and EntityCompare getter layouts.

The native and source checks establish stored MemoryPack records. They do not
establish when a getter is evaluated or which runtime entity or mission wins.
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
from scripts.game_data.memorypack.wrapper_members import derive_from_image, enum_widths_from_image


SCHEMA = "endfield.levelscript-getter-compare-native-contract.v1"
LABEL = "levelscriptGetterCompareNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_getter_compare_native.json"


def _contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    if (contract.get("schema") != SCHEMA or contract.get("status") != "exact-current-build"
            or contract.get("evidenceBoundary") != "exact"):
        raise ValueError(f"{LABEL}.contract:schema-status-boundary")
    routes = contract.get("routes")
    if (not isinstance(routes, list) or len(routes) != 2
            or sorted(route.get("tag") for route in routes) != [0x20, 0x29]):
        raise ValueError(f"{LABEL}.contract:selected-routes")
    expected_tail = {
        0x20: ["Param<BoolComparer>", "Param<MissionSystem.MissionState>",
               "Param<MissionSystem.MissionState>"],
        0x29: ["Param<EntityPtrComparer>", "Param<EntityPtr>", "Param<EntityPtr>"],
    }
    for route in routes:
        fields = route.get("fields")
        reads = route.get("readOrder")
        contexts = route.get("paramContexts")
        if (
            route.get("family") != "GetterBase" or route.get("nativeFamily") != "PureGetter"
            or route.get("memberCount") != 10 or route.get("inheritedMemberCount") != 7
            or not isinstance(fields, list) or len(fields) != 10
            or any(not isinstance(row, list) or len(row) != 3 for row in fields)
            or [row[1] for row in fields] != ["bool", "int32", "bool", "string", "int32",
                                               "bool", "bool", *expected_tail[route["tag"]]]
            or not isinstance(reads, list) or len(reads) != 10
            or [row.get("memberIndex") for row in reads] != list(range(10))
            or [(row.get("fieldName"), row.get("readKind")) for row in reads]
            != [(row[0], row[1]) for row in fields]
            or not isinstance(contexts, list) or [row.get("memberIndex") for row in contexts] != [7, 8, 9]
            or [row.get("elementTypeName") for row in contexts]
            != [fields[index][2].split("<", 1)[1][:-1] for index in (7, 8, 9)]
            or len(route.get("methods", [])) != 2 or len(route.get("codeWindows", [])) < 3
            or route.get("formatterTailJump", {}).get("targetRva") != route["methods"][0][3]
            or len(route.get("sourceReceipts", [])) < 1
            or any(len(row) != 5 for row in route["sourceReceipts"])
            or len({(row[0], row[2]) for row in route["sourceReceipts"]}) != len(route["sourceReceipts"])
        ):
            raise ValueError(f"{LABEL}.contract:route-shape={route.get('tag')}")
    return contract


def _call_target(image: Any, site: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:callsite={site:#x}")
    return site + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    base = image.pe.image_base
    wrappers = derive_from_image(image)
    switch = read_union_switch(
        image, "Beyond_Gameplay_Actions_PureGetterForMemoryPack", wrappers=wrappers,
    )
    dispatcher = contract["dispatcher"]
    if (switch["entryCount"] != dispatcher["switchEntryCount"]
            or int(switch["tableVa"], 16) != base + dispatcher["switchTableRva"]):
        raise ValueError(f"{LABEL}.native:switch-shape")
    table = image.pe.bytes_at_va(base + dispatcher["switchTableRva"], switch["entryCount"] * 4)
    if hashlib.sha256(table).hexdigest().upper() != dispatcher["switchTableSha256"].upper():
        raise ValueError(f"{LABEL}.native:switch-hash")
    widths = enum_widths_from_image(image)
    if any(widths.get(name) != width for name, width in contract["enumWidths"].items()):
        raise ValueError(f"{LABEL}.native:enum-width")
    extents = image.mapper.pdata_function_extents(image.pe)
    fragments = BodyIndex(image).chained_fragments
    for route in contract["routes"]:
        tag, branch = route["tag"], route["dispatcher"]
        entry = switch["entries"][tag]
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
            raise ValueError(f"{LABEL}.native:dispatch-entry={tag:#x}")
        image.check_windows([branch["branchWindow"]], label=LABEL)
        load = image.pe.bytes_at_va(base + branch["typeLoadRva"], 7)
        if load[:3] != b"\x48\x8B\x15" or load.hex().upper() != branch["typeLoadHex"].upper():
            raise ValueError(f"{LABEL}.native:type-load={tag:#x}")
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
            raise ValueError(f"{LABEL}.native:registered-wrapper={tag:#x}")
        wrapper = wrappers[definition]
        if (
            wrapper.wrapped_type != route["typeName"]
            or len(wrapper.inherited_members) != route["inheritedMemberCount"]
            or [[member.name.lstrip("_"), member.declared_type] for member in wrapper.members]
            != [[row[0], row[2]] for row in route["fields"]]
        ):
            raise ValueError(f"{LABEL}.native:wrapper-fields={tag:#x}")
        methods = [image.validate_method_row(row, label=LABEL) for row in route["methods"]]
        windows = route["codeWindows"]
        image.check_windows(windows, label=LABEL)
        source = image.method_pointer_va(image.metadata.methods[methods[0]])
        formatter = image.method_pointer_va(image.metadata.methods[methods[1]])
        expected_windows = [(source-base, extents[source]-base),
                            *((va-base, va+length-base) for va, length in fragments.get(source, ())),
                            (formatter-base, extents[formatter]-base)]
        if [(win["startRva"], win["endRva"]) for win in windows] != expected_windows:
            raise ValueError(f"{LABEL}.native:complete-method-windows={tag:#x}")
        tail = route["formatterTailJump"]
        tail_code = image.pe.bytes_at_va(base + tail["instructionRva"], 5)
        if (
            not windows[-1]["startRva"] <= tail["instructionRva"] < windows[-1]["endRva"]
            or tail_code[0] != 0xE9
            or tail_code.hex().upper() != tail["instructionHex"].upper()
            or tail["instructionRva"] + 5 + struct.unpack_from("<i", tail_code, 1)[0]
            != tail["targetRva"]
        ):
            raise ValueError(f"{LABEL}.native:formatter-forwarding={tag:#x}")
        count = route["memberCountInstruction"]
        image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
        if count["hex"].upper() != "4080FE0A":
            raise ValueError(f"{LABEL}.native:member-count-check={tag:#x}")
        ranges = [(win["startRva"], win["endRva"]) for win in windows[:-1]]
        previous = count["rva"]
        for read in route["readOrder"]:
            read_site, setter_site = read["readCallRva"], read["setterCallRva"]
            member = wrapper.members[read["memberIndex"]]
            method = image.metadata.methods[member.method_index]
            if (
                not previous < read_site < setter_site
                or not any(start <= read_site < setter_site < end for start, end in ranges)
                or _call_target(image, read_site, read["readCallHex"]) != read["readTargetRva"]
                or _call_target(image, setter_site, read["setterCallHex"]) != read["setterTargetRva"]
                or member.method_index != read["setterMethodIndex"]
                or member.declaring_wrapper != read["declaringWrapper"]
                or image.metadata.string(method.name_index) != f"set___{member.name}__"
                or image.method_pointer_va(method) != base + read["setterTargetRva"]
            ):
                raise ValueError(f"{LABEL}.native:ordered-read-setter={tag:#x}:{read['memberIndex']}")
            previous = setter_site
        for context in route["paramContexts"]:
            index = context["memberIndex"]
            if not route["readOrder"][index-1]["setterCallRva"] < context["instructionRva"] < route["readOrder"][index]["readCallRva"]:
                raise ValueError(f"{LABEL}.native:param-context-order={tag:#x}:{index}")
            method = image.metadata.methods[context["methodSpec"][0]]
            if (image.metadata.string(method.name_index) != "ReadValue"
                    or image.type_name(method.declaring_type) != "MemoryPack.MemoryPackReader"):
                raise ValueError(f"{LABEL}.native:param-reader-method={tag:#x}:{index}")
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
    checked = 0
    for route in contract["routes"]:
        prefix = bytes([route["tag"], route["memberCount"]])
        for path, digest, start, end, span_digest in route["sourceReceipts"]:
            data = (export_root / path).read_bytes()
            if (
                not 0 <= start < end <= len(data) or data[start:start+2] != prefix
                or hashlib.sha256(data).hexdigest().upper() != digest.upper()
                or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
                or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
                or ledger.get(path, {}).get("length") != len(data)
            ):
                raise ValueError(f"{LABEL}.source:receipt={path},offset={start}")
            checked += 1
    return checked


def validate_getter_compare_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Return the exact routes only when selected native and optional sources validate."""
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
        checked = 0
        if export_root is not None:
            if ledger_path is None or summary_path is None:
                raise ValueError(f"{LABEL}.source:explicit-summary-and-ledger-required")
            checked = _validate_sources(contract, Path(export_root), Path(ledger_path), Path(summary_path))
        return {"status": "validated", "evidenceBoundary": "exact",
                "routes": [{"family": route["family"], "tag": route["tag"],
                            "wrapperName": route["wrapperName"],
                            "fields": [field[:2] for field in route["fields"]]}
                           for route in contract["routes"]],
                "sourceReceiptsChecked": checked}
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as exc:
        return {"status": "validation_failed", "failedCheck": "selected-route-contract-native-or-source",
                "detail": str(exc), "validationFailures": [{"gate": "selected_route_contract_native_or_source"}]}


def main() -> int:
    audit = validate_getter_compare_native_contract(
        export_root=Path("export_full/game/Json"),
        ledger_path=Path("reports/animestudio/jsondata_current_files_latest.jsonl.gz"),
        summary_path=Path("reports/animestudio/jsondata_current_latest.json"),
    )
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
