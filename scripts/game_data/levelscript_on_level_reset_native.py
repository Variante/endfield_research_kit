"""Authenticate the selected OnLevelReset ActionHeader reader.

The reviewed contract pins ActionHeader `LevelEvent.OnLevelReset` (at
the contract's tag): the selected switch branch and wrapper, complete reader
and forwarding formatter, fourteen ordered reads and setters, and the typed
inherited validation parameter. Passing `--export-root`,
`--ledger` and `--summary` together also replays the reviewed source cursors
against the current JsonData ledger. The command prints its audit and exits
nonzero unless it validates. It proves stored header bytes; a live reset
event remains unobserved. This route has no own stored fields.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import generic_type_carrier, method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.codecs.levelscript.action_map import _Cursor


SCHEMA = "endfield.levelscript-on-level-reset-native.v1"
LABEL = "levelscriptOnLevelResetNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_on_level_reset_native.json"
_DECLARED_KIND = {
    "bool": "bool", "int": "int32", "string": "string",
    "Beyond.GEnums.ScopeName": "int32",
    "Beyond.Gameplay.Actions.FilterLevel": "int32",
    "Beyond.Gameplay.Actions.FilterMask": "int32",
    "Beyond.Gameplay.Actions.TriggerActiveDuring": "int32",
    "Beyond.Gameplay.Actions.Param`1<bool>": "Param<bool>",
    "Beyond.Gameplay.Actions.ParamOutput`1<bool>": "ParamOutput<bool>",
    "Beyond.Gameplay.Actions.Param`1<string>": "Param<string>",
    "Beyond.Gameplay.Actions.ParamOutput`1<string>": "ParamOutput<string>",
}
_GENERIC_SHAPES = {
    "Param<bool>": ("Beyond.Gameplay.Actions.Param`1", "System.Boolean", None),
    "ParamOutput<bool>": ("Beyond.Gameplay.Actions.ParamOutput`1", "System.Boolean", None),
    "Param<string>": ("Beyond.Gameplay.Actions.Param`1", "System.String", None),
    "ParamOutput<string>": ("Beyond.Gameplay.Actions.ParamOutput`1", "System.String", None),
}
_PRIMITIVE_TYPES = {2: "System.Boolean", 14: "System.String"}


def _contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    routes = contract.get("routes") or []
    if (
        contract.get("schema") != SCHEMA or contract.get("status") != "exact-current-build"
        or contract.get("evidenceBoundary") != "exact"
        or set(contract.get("nativeInputs") or {})
        != {"GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll"}
        or len(routes) != 1 or type(routes[0].get("tag")) is not int
        or not 0 <= routes[0]["tag"] < 0xFA
        or routes[0].get("tag") != 0x0077
        or routes[0].get("typeName") != "Beyond.Gameplay.Actions.LevelEvent.OnLevelReset"
        or not all(route.get("sourceReceipts") for route in routes)
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    for route in routes:
        fields = route.get("fields") or []
        native = route.get("nativeDeclaredTypes") or []
        reads = route.get("orderedReads") or []
        contexts = route.get("paramContexts") or []
        methods = route.get("methods") or []
        receipts = route.get("sourceReceipts") or []
        if (
            route.get("family") != "ActionHeader"
            or route.get("typeName") != "Beyond.Gameplay.Actions.LevelEvent.OnLevelReset"
            or route.get("serializedMemberCount") != len(fields)
            or len(fields) != 14
            or route.get("inheritedMemberCount") != 14
            or len(native) != len(fields)
            or [[name, _DECLARED_KIND.get(kind)] for name, kind in native] != fields
            or fields[14:] != []
            or [row.get("memberIndex") for row in reads] != list(range(len(fields)))
            or [row.get("fieldName") for row in reads] != [row[0] for row in fields]
            or [row.get("readKind") for row in reads] != [
                "generic" if kind in _GENERIC_SHAPES else kind for _, kind in fields
            ]
            or [row.get("memberIndex") for row in contexts]
            != [i for i, (_, kind) in enumerate(fields) if kind in _GENERIC_SHAPES]
            or len(methods) != 2 or len(route.get("codeWindows") or []) != 2
            or methods[0][1] != route.get("wrapperName")
            or not methods[1][1].startswith(route["wrapperName"] + "+")
            or [row[2] for row in methods] != ["Deserialize", "Deserialize"]
            or route.get("formatterTailJump", {}).get("targetRva") != methods[0][3]
            or any(not isinstance(row, list) or len(row) != 5 for row in receipts)
            or len({(row[0], row[2]) for row in receipts}) != len(receipts)
            or any(
                not isinstance(row[0], str) or "\\" in row[0]
                or PurePosixPath(row[0]).is_absolute()
                or ".." in PurePosixPath(row[0]).parts
                or not row[0].startswith("LevelScriptData/")
                for row in receipts
            )
        ):
            raise ValueError(f"{LABEL}.contract:route-shape")
    return contract


def _call_target(image: Any, site: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:callsite={site:#x}")
    return site + 5 + struct.unpack_from("<i", raw, 1)[0]


def _carrier_at(image: Any, raw: bytes, type_pointer: int) -> dict[str, Any]:
    pointer = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(pointer, 32)
    base_ptr = struct.unpack_from("<Q", carrier_raw)[0]
    return generic_type_carrier(
        raw, carrier_raw, image.pe.bytes_at_va(base_ptr, 16),
        type_pointer=type_pointer, type_count=len(image.metadata.types), source=LABEL,
    )


def _instance_dict(instance: Any) -> dict[str, Any]:
    row = instance.as_dict()
    row["arguments"] = list(row["arguments"])
    return row


def _validate_context(image: Any, context: dict[str, Any], kind: str) -> None:
    parent_expected, child_expected, nested_expected = _GENERIC_SHAPES[kind]
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:context-spec-index")
    spec_address = int(image.registration["methodSpecs"], 16) + index * 12
    spec = method_spec_record(
        image.pe.bytes_at_va(spec_address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source=LABEL, offset=spec_address,
    )
    method = image.metadata.methods[spec[0]]
    if (
        list(spec) != context["methodSpec"]
        or image.type_name(method.declaring_type) != "MemoryPack.MemoryPackReader"
        or image.metadata.string(method.name_index) != "ReadValue"
    ):
        raise ValueError(f"{LABEL}.native:context-reader")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:context-argument-count")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"] or raw[10] != 0x15:
        raise ValueError(f"{LABEL}.native:context-argument")
    carrier = _carrier_at(image, raw, argument.type_pointer_va)
    if (
        carrier != context["classCarrier"]
        or image.type_name(carrier["baseDefinitionIndex"]) != parent_expected
    ):
        raise ValueError(f"{LABEL}.native:context-parent")
    child_instance = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    if len(child_instance.arguments) != 1 or _instance_dict(child_instance) != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:context-instantiation")
    child_arg = child_instance.arguments[0]
    child_raw = bytes.fromhex(child_arg.raw_type_record_hex)
    reviewed = context["child"]
    if child_raw.hex().upper() != reviewed["rawHex"] or child_raw[10] != reviewed["kind"]:
        raise ValueError(f"{LABEL}.native:context-child-raw")
    if nested_expected is None:
        if child_raw[10] in (0x11, 0x12):
            definition = struct.unpack_from("<Q", child_raw)[0]
            actual = image.type_name(definition)
            if definition != reviewed.get("typeDefinition"):
                raise ValueError(f"{LABEL}.native:context-child-definition")
        else:
            actual = _PRIMITIVE_TYPES.get(child_raw[10])
        if actual != child_expected or reviewed.get("typeName") != child_expected:
            raise ValueError(f"{LABEL}.native:context-child-type")
        return
    if child_raw[10] != 0x15:
        raise ValueError(f"{LABEL}.native:context-list-kind")
    nested_carrier = _carrier_at(image, child_raw, child_arg.type_pointer_va)
    if (
        nested_carrier != reviewed.get("carrier")
        or image.type_name(nested_carrier["baseDefinitionIndex"]) != child_expected
        or reviewed.get("typeName") != child_expected
    ):
        raise ValueError(f"{LABEL}.native:context-list-carrier")
    nested_instance = image.instantiations.resolve_pointer(nested_carrier["classInstantiationPointerVa"])
    if len(nested_instance.arguments) != 1 or _instance_dict(nested_instance) != reviewed.get("classInstantiation"):
        raise ValueError(f"{LABEL}.native:context-list-instantiation")
    element_raw = bytes.fromhex(nested_instance.arguments[0].raw_type_record_hex)
    element_type = _PRIMITIVE_TYPES.get(element_raw[10])
    if (
        element_raw.hex().upper() != reviewed.get("elementRawHex")
        or element_raw[10] != reviewed.get("elementKind")
        or element_type != nested_expected
    ):
        raise ValueError(f"{LABEL}.native:context-list-element")


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    base = image.pe.image_base
    dispatcher = contract["dispatcher"]
    wrappers = derive_from_image(image)
    switch = read_union_switch(
        image, "Beyond_Gameplay_Actions_ActionHeaderForMemoryPack", wrappers=wrappers,
    )
    if (
        switch["entryCount"] != dispatcher["entryCount"]
        or int(switch["tableVa"], 16) != base + dispatcher["tableRva"]
    ):
        raise ValueError(f"{LABEL}.native:dispatcher")
    table = image.pe.bytes_at_va(base + dispatcher["tableRva"], dispatcher["entryCount"] * 4)
    if hashlib.sha256(table).hexdigest().upper() != dispatcher["tableSha256"].upper():
        raise ValueError(f"{LABEL}.native:switch-table")
    extents = image.mapper.pdata_function_extents(image.pe)
    chained = BodyIndex(image).chained_fragments
    for route in contract["routes"]:
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
            raise ValueError(f"{LABEL}.native:selected-wrapper={route['tag']:#x}")
        methods = [image.validate_method_row(row, label=LABEL) for row in route["methods"]]
        reader = image.method_pointer_va(image.metadata.methods[methods[0]])
        formatter = image.method_pointer_va(image.metadata.methods[methods[1]])
        expected = [
            (reader - base, extents[reader] - base),
            *((va - base, va + size - base) for va, size in chained.get(reader, ())),
            (formatter - base, extents[formatter] - base),
        ]
        windows = route["codeWindows"]
        if [(window["startRva"], window["endRva"]) for window in windows] != expected:
            raise ValueError(f"{LABEL}.native:complete-method-windows={route['tag']:#x}")
        image.check_windows(windows, label=LABEL)
        tail = route["formatterTailJump"]
        code = image.pe.bytes_at_va(base + tail["instructionRva"], 5)
        if (
            not windows[-1]["startRva"] <= tail["instructionRva"] < windows[-1]["endRva"]
            or code[0] != 0xE9 or code.hex().upper() != tail["instructionHex"].upper()
            or tail["instructionRva"] + 5 + struct.unpack_from("<i", code, 1)[0] != reader - base
        ):
            raise ValueError(f"{LABEL}.native:formatter-forwarding={route['tag']:#x}")
        count = route["memberCountInstruction"]
        image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
        count_raw = bytes.fromhex(count["hex"])
        reader_windows = windows[:-1]

        def in_reader_window(site: int, size: int) -> bool:
            return any(window["startRva"] <= site and site + size <= window["endRva"]
                       for window in reader_windows)

        if (
            not in_reader_window(count["rva"], len(count_raw))
            or not count["rva"] < route["orderedReads"][0]["readCallRva"]
            or len(count_raw) != 5 or count_raw[:4] != b"\x80\x7c\x24\x38"
            or count_raw[-1] != route["serializedMemberCount"]
        ):
            raise ValueError(f"{LABEL}.native:member-count={route['tag']:#x}")
        previous = count["rva"]
        for read in route["orderedReads"]:
            read_site, setter_site = read["readCallRva"], read["setterCallRva"]
            member = wrapper.members[read["memberIndex"]]
            setter = image.metadata.methods[member.method_index]
            if (
                not previous < read_site < setter_site
                or not in_reader_window(read_site, 5)
                or not in_reader_window(setter_site, 5)
                or _call_target(image, read_site, read["readCallHex"]) != read["readTargetRva"]
                or _call_target(image, setter_site, read["setterCallHex"]) != read["setterTargetRva"]
                or member.method_index != read["setterMethodIndex"]
                or member.declaring_wrapper != read["declaringWrapper"]
                or image.metadata.string(setter.name_index) != f"set___{member.name}__"
                or image.method_pointer_va(setter) != base + read["setterTargetRva"]
            ):
                raise ValueError(f"{LABEL}.native:ordered-read-setter={route['tag']:#x}:{read['memberIndex']}")
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
                raise ValueError(f"{LABEL}.native:context-order={route['tag']:#x}:{index}")
            _validate_context(image, context, route["fields"][index][1])


def _validate_sources(
    contract: dict[str, Any], export_root: Path, ledger_path: Path, summary_path: Path,
) -> int:
    summary = json.loads(summary_path.read_bytes())
    output = summary.get("provenance", {}).get("outputFiles", {})
    ledger_digest = sha256_file(ledger_path).upper()
    if (
        summary.get("status") != "complete"
        or ledger_path.stat().st_size != output.get("length")
        or ledger_digest != output.get("sha256", "").upper()
    ):
        raise ValueError(
            f"{LABEL}.source:summary-ledger-join={summary_path}:"
            f"expected=complete/{output.get('length')}/{output.get('sha256')},"
            f"actual={summary.get('status')}/{ledger_path.stat().st_size}/{ledger_digest}"
        )
    ledger = {}
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData":
                ledger[row["exportRelativePath"]] = row
    count = 0
    for route in contract["routes"]:
        prefix = bytes((route["tag"], route["serializedMemberCount"]))
        for path, digest, start, end, span_digest in route["sourceReceipts"]:
            data = (export_root / path).read_bytes()
            actual_digest = hashlib.sha256(data).hexdigest().upper()
            if actual_digest != digest.upper():
                raise ValueError(f"{LABEL}.source:source-sha256={path}:expected={digest}:actual={actual_digest}")
            row = ledger.get(path, {})
            if row.get("logicalSha256", "").upper() != digest.upper() or row.get("length") != len(data):
                raise ValueError(
                    f"{LABEL}.source:ledger-row={path}:expected={digest}/{len(data)},"
                    f"actual={row.get('logicalSha256')}/{row.get('length')}"
                )
            if not 0 <= start < end <= len(data):
                raise ValueError(f"{LABEL}.source:span-bounds={path}:start={start},end={end},length={len(data)}")
            if data[start:start + len(prefix)] != prefix:
                raise ValueError(
                    f"{LABEL}.source:union-prefix={path}@{start}:"
                    f"expected={prefix.hex().upper()},actual={data[start:start + len(prefix)].hex().upper()}"
                )
            actual_span_digest = hashlib.sha256(data[start:end]).hexdigest().upper()
            if actual_span_digest != span_digest.upper():
                raise ValueError(
                    f"{LABEL}.source:span-sha256={path}@{start}:{end}:"
                    f"expected={span_digest},actual={actual_span_digest}"
                )
            cursor = _Cursor(data, start)
            if cursor.byte("onLevelReset.tag") != route["tag"] or cursor.byte("onLevelReset.count") != route["serializedMemberCount"]:
                raise ValueError(f"{LABEL}.source:union-header={path}@{start}")
            for name, kind in route["fields"]:
                try:
                    cursor.value(kind, "onLevelReset." + name)
                except (ValueError, IndexError) as error:
                    raise ValueError(f"{LABEL}.source:field={path}@{cursor.offset}:{name}:{error}") from error
            if cursor.offset != end:
                raise ValueError(f"{LABEL}.source:cursor={path}@{start},end={cursor.offset},expected={end}")
            count += 1
    return count


def validate_levelscript_on_level_reset_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Fail closed on build, native body, generic type, or requested source drift."""
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
            return {"status": "mismatched", "failedGate": "UnityPlayer.dll",
                    "detail": "selected UnityPlayer.dll missing or different", "routeCount": 0}
        _validate_native(open_native_image(gate.gameassembly, gate.metadata), contract)
        count = 0
        if any(value is not None for value in (export_root, ledger_path, summary_path)):
            if not all(value is not None for value in (export_root, ledger_path, summary_path)):
                raise ValueError(f"{LABEL}.source:incomplete-paths")
            count = _validate_sources(contract, Path(export_root), Path(ledger_path), Path(summary_path))
        return {"status": "validated", "evidenceBoundary": "exact",
                "routeCount": len(contract["routes"]), "routes": contract["routes"],
                "sourceReceiptCount": count}
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        return {"status": "validation_failed", "failedGate": str(error).split(":", 1)[0],
                "detail": str(error)[:400], "routeCount": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)
    result = validate_levelscript_on_level_reset_native_contract(
        contract_path=args.contract, game_root=args.game_root, export_root=args.export_root,
        ledger_path=args.ledger, summary_path=args.summary,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "routes"}, indent=2))
    return 0 if result["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
