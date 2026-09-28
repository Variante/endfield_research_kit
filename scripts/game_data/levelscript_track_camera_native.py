"""Authenticate the selected EnterDollyTrackCamera ActionBase byte layout.

The stored route is authenticated by its native switch, complete generated
reader and formatter bodies, ordered reader/setter calls, 30 nested Param<T>
contexts, enum definition, and optional current source/ledger receipts.
This does not establish that the camera action executes in a live session.

The body after the eight inherited action fields is large (38 members).
Its `moveWay` member is `Param<TrackCameraMoveState>`, whose enum has
four-byte `int` storage and exactly two declared values, `Distance` and
`WayPoints`; both occur in current source. `codecs.levelscript.track_camera`
reads the four-member `Param` envelope and shared source/path tail with a
dedicated finite enum codec, so an unknown enum value fails closed. The
shared ActionMap reader admits the branch only while this validator passes.

Run as: python -m scripts.game_data.levelscript_track_camera_native
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
    generic_type_carrier,
    method_spec_record,
    method_spec_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-track-camera-native-contract.v1"
LABEL = "levelscriptTrackCameraNative"
CONTRACT_PATH = CONTRACTS_DIR / "levelscript_track_camera_native.json"
LAYOUT_PATH = Path(__file__).parent / "codecs" / "levelscript" / "action_map_layouts.json"

_NATIVE_TO_CODEC = {
    "bool": "bool", "int": "int32", "string": "string",
    "Beyond.GEnums.ScopeName": "int32",
    "Beyond.CameraBlendCurveKey": "CameraBlendCurveKey",
    "Cinemachine.CinemachineBlendDefinition+Style": "CinemachineBlendDefinition.Style",
    "float": "float", "UnityEngine.Vector3": "Vector3",
    "Beyond.Gameplay.Core.EntityPtr": "EntityPtr",
    "Beyond.Gameplay.Actions.EnterDollyTrackCamera+TrackCameraMoveState":
        "EnterDollyTrackCamera.TrackCameraMoveState",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _codec_kind(declared: str) -> str | None:
    prefix = "Beyond.Gameplay.Actions.Param`1<"
    if declared.startswith(prefix) and declared.endswith(">"):
        inner = _NATIVE_TO_CODEC.get(declared[len(prefix) : -1])
        return f"Param<{inner}>" if inner is not None else None
    return _NATIVE_TO_CODEC.get(declared)


def _contract(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_bytes())
    route = data["route"]
    fields = route["fields"]
    reads = data["readOrder"]
    contexts = data["paramContexts"]
    if (
        data.get("schema") != SCHEMA
        or data.get("status") != "exact-current-build"
        or data.get("evidenceBoundary") != "exact"
        or route.get("family") != "ActionBase"
        or route.get("typeName") != "Beyond.Gameplay.Actions.EnterDollyTrackCamera"
        or not isinstance(route.get("tag"), int)
        or not 0 <= route["tag"] < 0xFA
        or not isinstance(route.get("memberCount"), int)
        or not 0 < route["memberCount"] < 0xFF
        or not isinstance(route.get("inheritedMemberCount"), int)
        or not 0 <= route["inheritedMemberCount"] <= route["memberCount"]
        or not isinstance(fields, list) or len(fields) != route["memberCount"]
        or any(not isinstance(row, list) or len(row) != 3 or row[1] != _codec_kind(row[2])
               for row in fields)
        or [row[0] for row in fields].count("moveWay") != 1
        or not next(row for row in fields if row[0] == "moveWay")[1].endswith("TrackCameraMoveState>")
        or len(reads) != route["memberCount"]
        or [row["memberIndex"] for row in reads] != list(range(route["memberCount"]))
        or [row["memberIndex"] for row in contexts]
           != [index for index, row in enumerate(fields) if row[1].startswith("Param<")]
        or len(data["methods"]) != 2 or len(data["codeWindows"]) != 2
        or not data.get("sourceReceipts")
        or not data["enum"].get("members")
        or any(not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], str)
               or not isinstance(row[1], int) for row in data["enum"]["members"])
        or len({row[1] for row in data["enum"]["members"]}) != len(data["enum"]["members"])
        or data["enum"]["typeName"]
           != next(row for row in fields if row[0] == "moveWay")[2].split("<", 1)[1][:-1]
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    layouts = json.loads(LAYOUT_PATH.read_bytes())
    rows = [row for row in layouts.get("layouts", []) if
            (row.get("family"), row.get("tag")) == (route["family"], route["tag"])]
    layout = rows[0] if len(rows) == 1 else None
    cursor = layout.get("cursorEvidence") if layout else None
    receipts = data["sourceReceipts"]
    if (
        layouts.get("schema") != "endfield.action-map-layouts.v3"
        or layout is None
        or layout.get("nativeGate") != "levelscript_track_camera_native"
        or layout.get("wrapperName") != route["wrapperName"]
        or layout.get("memberCount") != route["memberCount"]
        or layout.get("fields") != [[name, kind] for name, kind, _native in fields]
        or not isinstance(cursor, dict)
        or not any([cursor.get("source"), cursor.get("sourceSha256"),
                    cursor.get("unionOffset"), cursor.get("endOffset")]
                   == receipt[:4] for receipt in receipts)
        or not isinstance(cursor.get("spanSha256"), str)
        or len(cursor["spanSha256"]) != 64
    ):
        raise ValueError(f"{LABEL}.contract:reviewed-layout-join")
    return data


def _call_target(image: Any, rva: int, expected_hex: str) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8 or raw.hex().upper() != expected_hex.upper():
        raise ValueError(f"{LABEL}.native:call={rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


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
    ):
        raise ValueError(f"{LABEL}.native:read-value-spec={row['memberIndex']}")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:read-value-arity={row['memberIndex']}")
    argument = instance.arguments[0]
    raw = bytes.fromhex(argument.raw_type_record_hex)
    carrier_pointer = struct.unpack_from("<Q", raw)[0]
    carrier_raw = image.pe.bytes_at_va(carrier_pointer, 32)
    base_pointer = struct.unpack_from("<Q", carrier_raw)[0]
    base_raw = image.pe.bytes_at_va(base_pointer, 16)
    carrier = generic_type_carrier(
        raw, carrier_raw, base_raw, type_pointer=argument.type_pointer_va,
        type_count=len(image.metadata.types), source=LABEL,
    )
    if image.type_name(carrier["baseDefinitionIndex"]) != "Beyond.Gameplay.Actions.Param`1":
        raise ValueError(f"{LABEL}.native:param-carrier={row['memberIndex']}")
    child = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
    if len(child.arguments) != 1:
        raise ValueError(f"{LABEL}.native:param-arity={row['memberIndex']}")
    element = bytes.fromhex(child.arguments[0].raw_type_record_hex)
    actual_type = il2cpp.runtime_type_name(image.pe, image.metadata, child.arguments[0].type_pointer_va)
    if (
        actual_type != expected_type
        or actual_type != row["elementTypeName"]
        or element[10] != row["elementTypeKind"]
        or element.hex().upper() != row["elementRawHex"].upper()
    ):
        raise ValueError(f"{LABEL}.native:param-element={row['memberIndex']}")


def _validate_native(image: Any, data: dict[str, Any]) -> None:
    route = data["route"]
    dispatcher = data["dispatcher"]
    base = image.pe.image_base
    wrappers = derive_from_image(image)
    switch = read_union_switch(image, "Beyond_Gameplay_Actions_ActionBaseForMemoryPack", wrappers=wrappers)
    entry = switch["entries"][route["tag"]]
    table_va = int(switch["tableVa"], 16)
    if (
        switch["entryCount"] != dispatcher["switchEntryCount"]
        or table_va != base + dispatcher["switchTableRva"]
        or _sha(image.pe.bytes_at_va(table_va, switch["entryCount"] * 4))
           != dispatcher["switchTableSha256"].upper()
        or int(entry["targetVa"], 16) != base + dispatcher["switchTargetRva"]
        or int(entry["bodyVa"], 16) != base + dispatcher["bodyRva"]
        or int(entry["usageCellVa"], 16) != base + dispatcher["usageCellRva"]
        or entry["typeDefinition"] != route["typeDefinition"]
        or entry["registeredTypeIndex"] != route["registeredTypeIndex"]
        or entry["wrapperName"] != route["wrapperName"]
    ):
        raise ValueError(f"{LABEL}.native:dispatch")
    image.check_windows([dispatcher["branchWindow"]], label=LABEL)
    wrapper = wrappers[route["typeDefinition"]]
    if (
        wrapper.name != route["wrapperName"]
        or wrapper.wrapped_type != route["typeName"]
        or len(wrapper.members) != route["memberCount"]
        or len(wrapper.inherited_members) != route["inheritedMemberCount"]
        or [[m.name.lstrip("_"), _codec_kind(m.declared_type or ""), m.declared_type]
            for m in wrapper.members] != route["fields"]
    ):
        raise ValueError(f"{LABEL}.native:wrapper-fields")

    extents = image.mapper.pdata_function_extents(image.pe)
    methods = [image.validate_method_row(row, label=LABEL) for row in data["methods"]]
    image.check_windows(data["codeWindows"], label=LABEL)
    for index, window in zip(methods, data["codeWindows"]):
        pointer = image.method_pointer_va(image.metadata.methods[index])
        if (
            pointer - base != window["startRva"]
            or extents.get(pointer, 0) - base != window["endRva"]
        ):
            raise ValueError(f"{LABEL}.native:method-extent")
    header = data["memberCountInstruction"]
    image.check_instruction_windows([[header["rva"], header["hex"]]], label=LABEL)
    if (
        not data["codeWindows"][0]["startRva"] < header["rva"]
        < data["codeWindows"][0]["endRva"]
        or bytes.fromhex(header["hex"])[-1] != route["memberCount"]
    ):
        raise ValueError(f"{LABEL}.native:member-count")
    previous = header["rva"]
    for read, member in zip(data["readOrder"], wrapper.members):
        if not previous < read["readCallRva"] < read["setterCallRva"] < data["codeWindows"][0]["endRva"]:
            raise ValueError(f"{LABEL}.native:read-order={read['memberIndex']}")
        if _call_target(image, read["readCallRva"], read["readCallHex"]) != read["readTargetRva"]:
            raise ValueError(f"{LABEL}.native:read-target={read['memberIndex']}")
        if (
            member.method_index != read["setterMethodIndex"]
            or image.method_pointer_va(image.metadata.methods[member.method_index]) - base
               != read["setterTargetRva"]
            or _call_target(image, read["setterCallRva"], read["setterCallHex"])
               != read["setterTargetRva"]
        ):
            raise ValueError(f"{LABEL}.native:setter={read['memberIndex']}")
        previous = read["setterCallRva"]
    contexts = data["paramContexts"]
    for context in contexts:
        index = context["memberIndex"]
        read = data["readOrder"][index]
        if not (
            data["readOrder"][index - 1]["setterCallRva"]
            < context["instructionRva"] < read["readCallRva"]
        ):
            raise ValueError(f"{LABEL}.native:context-order={index}")
        expected_type = route["fields"][index][2].split("<", 1)[1][:-1]
        _validate_context(image, context, expected_type)
    if len({data["readOrder"][r["memberIndex"]]["readTargetRva"] for r in contexts}) != 1:
        raise ValueError(f"{LABEL}.native:param-reader-target")

    enum = data["enum"]
    definition = enum["typeDefinition"]
    if image.type_name(definition) != enum["typeName"] or enum["underlyingType"] != "int":
        raise ValueError(f"{LABEL}.native:enum-type")
    value_fields = [field for field in image.metadata.fields_for(image.metadata.types[definition])
                    if image.metadata.string(field.name_index) == "value__"]
    if len(value_fields) != 1:
        raise ValueError(f"{LABEL}.native:enum-width")
    type_table = int(image.registration["types"], 16)
    type_va = image.pe.u64_at_va(type_table + value_fields[0].type_index * 8)
    if il2cpp.runtime_type_name(image.pe, image.metadata, type_va) != enum["underlyingType"]:
        raise ValueError(f"{LABEL}.native:enum-width")
    members = il2cpp.native_enum_members(
        image.metadata, BodyIndex(image).enum_defaults, image.pe, image.registration,
        enum["typeName"],
    )
    if [[r["name"], r["id"]] for r in members] != enum["members"]:
        raise ValueError(f"{LABEL}.native:enum-members")


def _validate_sources(data: dict[str, Any], export_root: Path, ledger_path: Path) -> None:
    from scripts.game_data.codecs.levelscript.track_camera import decode_track_camera_action

    ledger: dict[str, dict[str, Any]] = {}
    with gzip.open(ledger_path, "rt", encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData":
                ledger[row["exportRelativePath"]] = row
    if not ledger:
        raise ValueError(f"{LABEL}.source:missing-ledger")
    layouts = json.loads(LAYOUT_PATH.read_bytes())
    cursor = next(row["cursorEvidence"] for row in layouts["layouts"] if
                  (row.get("family"), row.get("tag")) ==
                  (data["route"]["family"], data["route"]["tag"]))
    enum_values = {value: name for name, value in data["enum"]["members"]}
    for path, digest, start, end, move_start, move_end, move_digest in data["sourceReceipts"]:
        if not path.startswith("LevelScriptData/"):
            raise ValueError(f"{LABEL}.source:path={path}")
        payload = (export_root / path).read_bytes()
        if (
            _sha(payload) != digest.upper()
            or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
            or not 0 <= start < move_start < move_end <= end <= len(payload)
            or _sha(payload[move_start:move_end]) != move_digest.upper()
        ):
            raise ValueError(f"{LABEL}.source:receipt={path}@{start}")
        if path == cursor["source"] and start == cursor["unionOffset"]:
            if _sha(payload[start:end]) != cursor["spanSha256"].upper():
                raise ValueError(f"{LABEL}.source:layout-span={path}@{start}")
        decoded, consumed = decode_track_camera_action(payload, start, data["route"], enum_values)
        if (
            consumed != end
            or decoded["fieldSpans"]["moveWay"] != [move_start, move_end]
            or decoded["fields"]["moveWay"]["value"] not in enum_values
        ):
            raise ValueError(f"{LABEL}.source:cursor={path}@{start}")


def validate_track_camera_native_contract(
    *, contract_path: Path = CONTRACT_PATH, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Fail closed on installed-build, contract, body, or source drift."""
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
            if ledger_path is None:
                raise ValueError(f"{LABEL}.source:explicit-ledger-required")
            _validate_sources(data, Path(export_root), Path(ledger_path))
        return {"status": "validated", "evidenceBoundary": "exact",
                "route": {"family": "ActionBase", "tag": data["route"]["tag"],
                          "wrapperName": data["route"]["wrapperName"],
                          "fields": [[name, kind] for name, kind, _native in data["route"]["fields"]]},
                "enumMembers": data["enum"]["members"],
                "sourceReceiptsChecked": len(data["sourceReceipts"]) if export_root else 0}
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as exc:
        detail = str(exc)
        check = detail.split(f"{LABEL}.", 1)[1].split(":", 1)[0] if detail.startswith(f"{LABEL}.") else "contract-native-or-source"
        return {"status": "validation_failed", "failedCheck": check,
                "detail": detail, "validationFailures": [{"gate": check, "actual": detail[:500]}]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--export-root", type=Path, help="current exported game/Json root")
    parser.add_argument("--ledger", type=Path, help="current JsonData per-file JSONL.gz ledger")
    args = parser.parse_args(argv)
    result = validate_track_camera_native_contract(
        game_root=args.game_root, export_root=args.export_root, ledger_path=args.ledger,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
