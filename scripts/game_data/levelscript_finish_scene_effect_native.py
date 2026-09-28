"""Authenticate the selected FinishSceneEffect ActionBase stored layout."""

from __future__ import annotations

import gzip
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.levelscript_two_routes_native import _validate_context
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-finish-scene-effect-native-contract.v1"
LABEL = "levelscriptFinishSceneEffectNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_finish_scene_effect_native.json"


def _contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    if contract.get("schema") != SCHEMA:
        raise ValueError(f"{LABEL}.contract:schema")
    if contract.get("status") != "exact-current-build":
        raise ValueError(f"{LABEL}.contract:status")
    route = contract["route"]
    fields = route["fields"]
    reads = contract["orderedReads"]
    contexts = contract["nestedContexts"]
    if (
        contract.get("evidenceBoundary") != "exact"
        or route.get("family") != "ActionBase"
        or not isinstance(route.get("tag"), int)
        or not 0 <= route["tag"] < contract["dispatcher"]["switchEntryCount"]
        or not isinstance(route.get("serializedMemberCount"), int)
        or not isinstance(route.get("inheritedMemberCount"), int)
        or not 0 <= route["inheritedMemberCount"] <= route["serializedMemberCount"]
        or len(fields) != route["serializedMemberCount"]
        or len(reads) != route["serializedMemberCount"]
        or [(row["fieldName"], row["readKind"]) for row in reads] != [tuple(row) for row in fields]
        or [row["memberIndex"] for row in reads] != list(range(route["serializedMemberCount"]))
        or len(contract["methods"]) != 2
        or len(contract["codeWindows"]) != 2
        or [row["memberIndex"] for row in contract["ownSetters"]]
        != list(range(route["inheritedMemberCount"], route["serializedMemberCount"]))
        or [(row["memberIndex"], row["elementTypeName"]) for row in contexts]
        != [(row["memberIndex"], {"Param<int>": "System.Int32", "Param<bool>": "System.Boolean"}.get(
            fields[row["memberIndex"]][1])) for row in contract["ownSetters"]]
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def _call_target(image: Any, rva: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:call={rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


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
    if (
        struct.unpack_from("<I", table, tag * 4)[0] != branch["switchTargetRva"]
        or int(entry["targetVa"], 16) != base + branch["switchTargetRva"]
        or int(entry["bodyVa"], 16) != base + branch["bodyRva"]
        or entry["wrapperName"] != route["wrapperName"]
        or entry["typeDefinition"] != route["typeDefinition"]
        or entry["registeredTypeIndex"] != route["registeredTypeIndex"]
    ):
        raise ValueError(f"{LABEL}.native:dispatch-entry")
    image.check_windows([branch["branchWindow"]], label=LABEL)
    load_rva = branch["typeLoadRva"]
    load = image.pe.bytes_at_va(base + load_rva, 7)
    if load[:3] != b"\x48\x8b\x15" or load.hex().upper() != branch["typeLoadHex"]:
        raise ValueError(f"{LABEL}.native:type-load")
    cell_va = base + load_rva + 7 + struct.unpack_from("<i", load, 3)[0]
    usage = image.pe.bytes_at_va(cell_va, 8)
    index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1, source=LABEL, offset=cell_va,
    )
    if (
        cell_va - base != branch["usageCellRva"]
        or usage.hex().upper() != branch["usageRawHex"]
        or index != route["registeredTypeIndex"]
    ):
        raise ValueError(f"{LABEL}.native:registered-type-usage")
    wrapper = wrappers[route["typeDefinition"]]
    normalized_kinds = {
        "bool": "bool", "int": "int32", "string": "string",
        "Beyond.GEnums.ScopeName": "int32",
        "Beyond.Gameplay.Actions.Param`1<int>": "Param<int>",
        "Beyond.Gameplay.Actions.Param`1<bool>": "Param<bool>",
    }
    if (
        wrapper.name != route["wrapperName"]
        or wrapper.wrapped_type != route["typeName"]
        or len(wrapper.members) != route["serializedMemberCount"]
        or len(wrapper.own_members) != route["serializedMemberCount"] - route["inheritedMemberCount"]
        or [[member.name.lstrip("_"), normalized_kinds.get(member.declared_type)]
            for member in wrapper.members] != route["fields"]
    ):
        raise ValueError(f"{LABEL}.native:wrapper-fields")

    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    windows = contract["codeWindows"]
    image.check_windows(windows, label=LABEL)
    image.check_instruction_windows([[contract["memberCountInstruction"]["rva"],
                                     contract["memberCountInstruction"]["hex"]]], label=LABEL)
    extents = image.mapper.pdata_function_extents(image.pe)
    for method_index, window in zip(methods, windows):
        pointer = image.method_pointer_va(image.metadata.methods[method_index])
        if (
            window["startRva"] != pointer - base
            or window["endRva"] != extents.get(pointer, 0) - base
        ):
            raise ValueError(f"{LABEL}.native:method-extent")
    source_window = windows[0]
    previous = contract["memberCountInstruction"]["rva"]
    for read in contract["orderedReads"]:
        site = read["sourceCallsiteRva"]
        if not previous < site < source_window["endRva"]:
            raise ValueError(f"{LABEL}.native:read-order={read['memberIndex']}")
        if _call_target(image, site, read["sourceCallHex"]) != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:read-target={read['memberIndex']}")
        previous = site
    for setter in contract["ownSetters"]:
        index = setter["memberIndex"]
        method_index = setter["methodIndex"]
        member = wrapper.members[index]
        method = image.metadata.methods[method_index]
        if (
            member.method_index != method_index
            or member.declaring_wrapper != setter["declaringWrapper"]
            or image.metadata.string(method.name_index) != setter["setterName"]
            or image.method_pointer_va(method) != base + setter["targetRva"]
            or not contract["orderedReads"][index]["sourceCallsiteRva"]
            < setter["callsiteRva"] < source_window["endRva"]
            or _call_target(image, setter["callsiteRva"], setter["callHex"])
            != setter["targetRva"]
        ):
            raise ValueError(f"{LABEL}.native:setter={index}")
    for context in contract["nestedContexts"]:
        index = context["memberIndex"]
        if not (
            contract["orderedReads"][index - 1]["sourceCallsiteRva"]
            < context["instructionRva"]
            < contract["orderedReads"][index]["sourceCallsiteRva"]
        ):
            raise ValueError(f"{LABEL}.native:context-order={index}")
        _validate_context(image, context, context["elementTypeName"])


def _validate_sources(contract: dict[str, Any], export_root: Path, ledger_path: Path) -> None:
    """Join exported bytes to the JsonData registry's per-file ledger."""
    ledger: dict[str, dict[str, Any]] = {}
    with gzip.open(ledger_path, "rt", encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData":
                ledger[row["exportRelativePath"]] = row
    if not ledger:
        raise ValueError(f"{LABEL}.source:expected-JsonData-per-file-ledger")
    for path, digest, start, end, span_digest in contract["sourceReceipts"]:
        data = (export_root / path).read_bytes()
        if (
            not 0 <= start < end <= len(data)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
            or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
        ):
            raise ValueError(f"{LABEL}.source:receipt={path}")


def validate_finish_scene_effect_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Validate native layout, optionally joining current source receipts."""
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
                "route": {"family": "ActionBase", "tag": contract["route"]["tag"],
                          "wrapperName": contract["route"]["wrapperName"],
                          "fields": contract["route"]["fields"]},
                "sourceReceiptsChecked": len(contract["sourceReceipts"]) if export_root else 0}
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as exc:
        failure = str(exc)
        check = failure.split(".contract:", 1)[1] if ".contract:" in failure else "contract-native-or-source"
        return {"status": "validation_failed", "failedCheck": check,
                "detail": failure, "validationFailures": [{"gate": check,
                                                       "actual": str(exc)[:500]}]}


def main() -> int:
    audit = validate_finish_scene_effect_native_contract()
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
