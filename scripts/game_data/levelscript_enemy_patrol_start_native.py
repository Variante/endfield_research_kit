"""Authenticate the selected EnemyPatrolStart stored action and source cursors.

This proves serialized patrol-start arguments on the selected installed client.
It does not prove that the action executes or changes an enemy's patrol state.
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


SCHEMA = "endfield.levelscript-enemy-patrol-start-native-contract.v1"
LABEL = "levelscriptEnemyPatrolStartNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_enemy_patrol_start_native.json"
LAYOUT_PATH = Path(__file__).parent / "codecs" / "levelscript" / "action_map_layouts.json"

NATIVE_KINDS = {
    "bool": "bool", "int": "int32", "string": "string",
    "Beyond.GEnums.ScopeName": "int32",
    "Beyond.Gameplay.Actions.Param`1<ulong>": "Param<ulong>",
    "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.EntityPtr>": "Param<EntityPtr>",
}


def _contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    route = contract.get("route", {})
    fields = route.get("fields", [])
    reads = route.get("readOrder", [])
    contexts = route.get("paramContexts", [])
    if (
        contract.get("schema") != SCHEMA or contract.get("status") != "exact-current-build"
        or contract.get("evidenceBoundary") != "exact"
        or route.get("family") != "ActionBase"
        or route.get("typeName") != "Beyond.Gameplay.Actions.EnemyPatrolStart"
        or not isinstance(route.get("tag"), int) or not 0 <= route["tag"] < 0xFA
        or route.get("memberCount") != len(fields)
        or route.get("inheritedMemberCount") != len(fields) - 2
        or not isinstance(fields, list) or len(fields) < 3
        or any(not isinstance(row, list) or len(row) != 3 for row in fields)
        or [NATIVE_KINDS.get(row[2]) for row in fields] != [row[1] for row in fields]
        or [row[1] for row in fields[-2:]] != ["Param<ulong>", "Param<EntityPtr>"]
        or [row.get("memberIndex") for row in reads] != list(range(len(fields)))
        or [(row.get("fieldName"), row.get("readKind")) for row in reads]
        != [(row[0], row[1]) for row in fields]
        or [row.get("memberIndex") for row in contexts]
        != list(range(route["inheritedMemberCount"], len(fields)))
        or [row.get("elementTypeName") for row in contexts]
        != [field[2].split("<", 1)[1][:-1] for field in fields[-2:]]
        or len(route.get("methods", [])) != 2 or len(route.get("codeWindows", [])) != 2
        or route.get("formatterTailJump", {}).get("targetRva") != route["methods"][0][3]
        or len(route.get("sourceReceipts", [])) < 1
        or any(len(row) != 5 for row in route["sourceReceipts"])
        or len({(row[0], row[2]) for row in route["sourceReceipts"]}) != len(route["sourceReceipts"])
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    layouts = json.loads(LAYOUT_PATH.read_bytes())
    matches = [row for row in layouts.get("layouts", []) if
               (row.get("family"), row.get("tag")) == (route["family"], route["tag"])]
    layout = matches[0] if len(matches) == 1 else None
    if (
        layouts.get("schema") != "endfield.action-map-layouts.v3"
        or layout is None
        or layout.get("nativeGate") != "levelscript_enemy_patrol_start_native"
        or layout.get("wrapperName") != route["wrapperName"]
        or layout.get("memberCount") != route["memberCount"]
        or layout.get("fields") != [field[:2] for field in fields]
        or not any(
            layout.get("cursorEvidence", {}).get("source") == path
            and layout["cursorEvidence"].get("sourceSha256", "").upper() == digest.upper()
            and layout["cursorEvidence"].get("unionOffset") == start
            and layout["cursorEvidence"].get("endOffset") == end
            and layout["cursorEvidence"].get("spanSha256", "").upper() == span.upper()
            for path, digest, start, end, span in route["sourceReceipts"]
        )
    ):
        raise ValueError(f"{LABEL}.contract:reviewed-layout-join")
    return contract


def _call_target(image: Any, site: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:callsite={site:#x}")
    return site + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_context(image: Any, context: dict[str, Any], expected_type: str) -> None:
    """Resolve the actual ReadValue<Param<T>> MethodSpec and its element."""
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:param-spec-index={context['memberIndex']}")
    address = int(image.registration["methodSpecs"], 16) + index * 12
    spec = method_spec_record(
        image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source=LABEL, offset=address,
    )
    method = image.metadata.methods[spec[0]]
    instance = image.instantiations.resolve(spec[2])
    if (
        list(spec) != context["methodSpec"] or len(instance.arguments) != 1
        or image.type_name(method.declaring_type) != "MemoryPack.MemoryPackReader"
        or image.metadata.string(method.name_index) != "ReadValue"
    ):
        raise ValueError(f"{LABEL}.native:param-readvalue={context['memberIndex']}")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    if raw.hex().upper() != context["argumentRawHex"].upper() or raw[10] != 0x15:
        raise ValueError(f"{LABEL}.native:param-type={context['memberIndex']}")
    carrier_pointer = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(carrier_pointer, 32)
    base_pointer = struct.unpack_from("<Q", carrier_raw)[0]
    base_raw = image.pe.bytes_at_va(base_pointer, 16)
    carrier = generic_type_carrier(
        raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
        type_count=len(image.metadata.types), source=LABEL,
    )
    if (
        carrier != context["classCarrier"]
        or image.type_name(carrier["baseDefinitionIndex"])
           != "Beyond.Gameplay.Actions.Param`1"
    ):
        raise ValueError(f"{LABEL}.native:param-carrier={context['memberIndex']}")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    child_row = child.as_dict()
    child_row["arguments"] = list(child_row["arguments"])
    if len(child.arguments) != 1 or child_row != context["classInstantiation"]:
        raise ValueError(f"{LABEL}.native:param-instantiation={context['memberIndex']}")
    element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
    actual_type = il2cpp.runtime_type_name(
        image.pe, image.metadata, child.arguments[0].type_pointer_va,
    )
    if (
        actual_type != expected_type
        or actual_type != context["elementTypeName"]
        or element.hex().upper() != context["elementRawHex"].upper()
        or element[10] != context["elementTypeKind"]
    ):
        raise ValueError(f"{LABEL}.native:param-element={context['memberIndex']}")
    if expected_type == "ulong":
        if element[10] != 0x0B or context["elementTypeDefinition"] is not None:
            raise ValueError(f"{LABEL}.native:param-ulong={context['memberIndex']}")
    elif expected_type == "Beyond.Gameplay.Core.EntityPtr":
        definition = struct.unpack_from("<Q", element)[0]
        if (
            element[10] != 0x11
            or definition != context["elementTypeDefinition"]
            or image.type_name(definition) != expected_type
        ):
            raise ValueError(f"{LABEL}.native:param-entity-ptr={context['memberIndex']}")
    else:
        raise ValueError(f"{LABEL}.native:param-unsupported={context['memberIndex']}")


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
    if (
        bytes.fromhex(count["hex"])[:4] != b"\x80\x7c\x24\x38"
        or bytes.fromhex(count["hex"])[4:] != bytes((route["memberCount"],))
    ):
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
    from scripts.game_data.codecs.levelscript.action_map import _Cursor

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
    prefix = bytes((route["tag"], route["memberCount"]))
    for path,digest,start,end,span_digest in route["sourceReceipts"]:
        data = (export_root / path).read_bytes()
        if (
            not 0 <= start < end <= len(data) or data[start:start+len(prefix)] != prefix
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
            or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
            or ledger.get(path, {}).get("length") != len(data)
        ):
            raise ValueError(f"{LABEL}.source:receipt={path},offset={start}")
        cursor = _Cursor(data, start + len(prefix))
        decoded = {
            name: cursor.value(kind, f"{LABEL}.source.{name}")
            for name, kind, _native in route["fields"]
        }
        if (
            cursor.offset != end
            or decoded[route["fields"][-2][0]] is None
            or decoded[route["fields"][-1][0]] is None
        ):
            raise ValueError(f"{LABEL}.source:cursor={path},offset={start},end={cursor.offset}")
    return len(route["sourceReceipts"])


def validate_enemy_patrol_start_native_contract(
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
            return {"status": gate.status, "failedCheck": "installed-native-inputs",
                    "detail": gate.detail,
                    "validationFailures": [{"gate": "installed-native-inputs",
                                            "actual": gate.detail[:500]}]}
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
        failure = str(exc)
        check = (failure.split(".contract:", 1)[1] if ".contract:" in failure
                 else failure.split(".native:", 1)[1] if ".native:" in failure
                 else failure.split(".source:", 1)[1] if ".source:" in failure
                 else "selected-route-contract-native-or-source")
        return {"status": "validation_failed", "failedCheck": check,
                "detail": failure,
                "validationFailures": [{"gate": check, "actual": failure[:500]}]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path,
                        help="Selected Endfield_Data directory (otherwise use configured game root)")
    parser.add_argument("--export-root", type=Path,
                        help="JsonData export root for source cursor replay")
    parser.add_argument("--ledger", type=Path,
                        help="Current JsonData per-file ledger .jsonl.gz")
    parser.add_argument("--summary", type=Path,
                        help="Current JsonData corpus summary .json")
    args = parser.parse_args()
    audit=validate_enemy_patrol_start_native_contract(
        game_root=args.game_root,
        export_root=args.export_root,
        ledger_path=args.ledger,
        summary_path=args.summary,
    )
    print(json.dumps(audit,indent=2))
    return 0 if audit["status"]=="validated" else 1


if __name__=="__main__":
    raise SystemExit(main())
