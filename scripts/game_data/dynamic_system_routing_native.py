"""Validate selected DynamicStreaming data-type to system routing.

The body called by GetSystemByDataType uses a native jump table. A separately
registered switch implements the same mapping; both must agree for every
selected EDynamicSceneData member. Current DataIndex records are authenticated
and joined to the route, without claiming live grid activation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_data_index_native import (
    audit_current_main as audit_data_index_main,
    validate_native_layout as validate_data_index_layout,
)
from scripts.game_data.dynamic_stream_area_corpus import DEFAULT_CLI, DEFAULT_LEDGER, DEFAULT_OUTER
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import field_defaults, native_enum_members
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_system_routing_native.json"
SCHEMA = "endfield.dynamic-system-routing-native-contract.v1"
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_system_routing_native_latest.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports/animestudio/dynamic_system_routing_native_latest.md"


class DynamicSystemRoutingError(ValueError):
    """A native route witness or current-corpus join differs."""


def _signed32(value: int) -> int:
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def _registered_switch(raw: bytes, data_type: int) -> int:
    """Execute only the reviewed x64 compare/branch/immediate subset."""
    pc, edx, ecx, al = 0, _signed32(data_type), 0, 0
    zero = greater = False
    for _step in range(128):
        if not 0 <= pc < len(raw):
            raise DynamicSystemRoutingError(f"registered switch branch outside code window at {pc}")
        tail = raw[pc:]
        if tail.startswith(b"\x83\xc2") or tail.startswith(b"\x83\xea"):
            immediate = struct.unpack_from("<b", raw, pc + 2)[0]
            edx = _signed32(edx + immediate if raw[pc + 1] == 0xC2 else edx - immediate)
            zero, greater = edx == 0, edx > 0
            pc += 3
        elif tail.startswith(b"\xb9"):
            ecx = struct.unpack_from("<I", raw, pc + 1)[0]
            pc += 5
        elif tail.startswith(b"\x3b\xd1"):
            zero, greater = edx == _signed32(ecx), edx > _signed32(ecx)
            pc += 2
        elif tail.startswith(b"\x83\xfa"):
            immediate = struct.unpack_from("<b", raw, pc + 2)[0]
            zero, greater = edx == immediate, edx > immediate
            pc += 3
        elif tail.startswith(b"\x85\xd2"):
            zero, greater = edx == 0, edx > 0
            pc += 2
        elif tail.startswith(b"\x32\xc9"):
            ecx &= ~0xFF
            zero, greater = True, False
            pc += 2
        elif tail.startswith(b"\xb1"):
            ecx = (ecx & ~0xFF) | raw[pc + 1]
            pc += 2
        elif tail.startswith(b"\x8a\xc1"):
            al = ecx & 0xFF
            pc += 2
        elif tail.startswith(b"\xc3"):
            return al
        else:
            branch = None
            if tail.startswith(b"\x0f\x84"):
                branch = (zero, 6, struct.unpack_from("<i", raw, pc + 2)[0])
            elif tail.startswith(b"\x0f\x85"):
                branch = (not zero, 6, struct.unpack_from("<i", raw, pc + 2)[0])
            elif tail.startswith(b"\x0f\x8f"):
                branch = (greater, 6, struct.unpack_from("<i", raw, pc + 2)[0])
            elif tail[:1] in (b"\x74", b"\x75", b"\x7f", b"\xeb"):
                opcode = raw[pc]
                take = {0x74: zero, 0x75: not zero, 0x7F: greater, 0xEB: True}[opcode]
                branch = (take, 2, struct.unpack_from("<b", raw, pc + 1)[0])
            elif tail.startswith(b"\xe9"):
                branch = (True, 5, struct.unpack_from("<i", raw, pc + 1)[0])
            if branch is None:
                raise DynamicSystemRoutingError(
                    f"registered switch has unreviewed opcode at {pc}: {tail[:8].hex()}"
                )
            take, size, displacement = branch
            pc += size + (displacement if take else 0)
    raise DynamicSystemRoutingError("registered switch did not return within 128 instructions")


def _rel_call_target(raw: bytes, prefix: bytes, method_rva: int, label: str) -> int:
    position = raw.find(prefix)
    if position < 0 or raw.find(prefix, position + 1) >= 0:
        raise DynamicSystemRoutingError(f"{label}: call-site pattern differs")
    opcode = position + len(prefix) - 1
    if raw[opcode] != 0xE8 or opcode + 5 > len(raw):
        raise DynamicSystemRoutingError(f"{label}: relative call is truncated")
    return method_rva + opcode + 5 + struct.unpack_from("<i", raw, opcode + 1)[0]


def _called_route(
    image: Any, spec: dict[str, Any], data_ids: list[int],
) -> tuple[dict[int, int], dict[str, int]]:
    """Decode the selected base-body jump table and each three-byte target."""
    rva = int(spec["rva"])
    code = image.pe.bytes_at_va(image.pe.image_base + rva, int(spec["codeExtent"]))
    if hashlib.sha256(code).hexdigest().upper() != spec["codeSha256"].upper():
        raise DynamicSystemRoutingError("called route dispatcher code window differs")
    if not (
        code[:2] == b"\x83\xc2" and code[3:5] == b"\x83\xfa"
        and code[6:8] == b"\x0f\x87" and code[12:18] == b"\x48\x63\xc2\x48\x8d\x15"
        and code[22:25] == b"\x8b\x8c\x82" and code[29:] == b"\x48\x03\xca\xff\xe1"
    ):
        raise DynamicSystemRoutingError("called route dispatcher instruction shape differs")
    first = -struct.unpack_from("<b", code, 2)[0]
    count = code[5] + 1
    default_rva = rva + 12 + struct.unpack_from("<i", code, 8)[0]
    image_base_rva = rva + 22 + struct.unpack_from("<i", code, 18)[0]
    table_rva = struct.unpack_from("<i", code, 25)[0] + image_base_rva
    if image_base_rva != 0 or count != int(spec["tableCount"]) or table_rva != int(spec["tableRva"]):
        raise DynamicSystemRoutingError("called route table base, count, or RVA differs")
    table = image.pe.bytes_at_va(image.pe.image_base + table_rva, count * 4)
    if hashlib.sha256(table).hexdigest().upper() != spec["tableSha256"].upper():
        raise DynamicSystemRoutingError("called route jump table differs")

    routes: dict[int, int] = {}
    for data_id in data_ids:
        target = (
            struct.unpack_from("<I", table, (data_id - first) * 4)[0]
            if first <= data_id < first + count else default_rva
        )
        stub = image.pe.bytes_at_va(image.pe.image_base + target, 3)
        if stub[:1] == b"\xb0" and stub[2:] == b"\xc3":
            routes[data_id] = stub[1]
        elif stub == b"\x32\xc0\xc3":
            routes[data_id] = 0
        else:
            raise DynamicSystemRoutingError(f"called route Type={data_id} has unreviewed target stub")
    return routes, {"firstType": first, "tableCount": count, "defaultRva": default_rva}


def validate_native_routes(
    gameassembly: Path, metadata: Path,
) -> tuple[dict[int, int], dict[int, str], dict[int, str], str, dict[str, str]]:
    """Authenticate both native routes and decode correctly typed enum IDs."""
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="dynamic_system_routing", status="validated")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicSystemRoutingError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = Path(gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file():
        raise DynamicSystemRoutingError(f"installed_native_inputs:missing:{unity}")
    unity_sha = sha256_file(unity).upper()
    if unity_sha != inputs["unityPlayerSha256"].upper():
        raise DynamicSystemRoutingError("installed_native_inputs:mismatched:UnityPlayer.dll hash differs")
    receipt = {
        "gameAssemblySha256": gate.gameassembly_sha256.upper(),
        "metadataSha256": gate.metadata_sha256.upper(),
        "unityPlayerSha256": unity_sha,
    }
    image = open_native_image(Path(gameassembly), Path(metadata))
    layout = contract["layout"]
    defaults = field_defaults(image.metadata)
    data_rows = native_enum_members(
        image.metadata, defaults, image.pe, image.registration, layout["dataEnumType"],
    )
    system_rows = native_enum_members(
        image.metadata, defaults, image.pe, image.registration, layout["systemEnumType"],
    )
    data_enum = {int(row["id"]): row["name"] for row in data_rows}
    system_enum = {int(row["id"]): row["name"] for row in system_rows}
    if len(data_enum) != len(data_rows) or len(system_enum) != len(system_rows):
        raise DynamicSystemRoutingError("selected enum has duplicate numeric IDs")
    if system_enum.get(0) != "None":
        raise DynamicSystemRoutingError("selected EDynamicSystem.None differs")

    methods: dict[int, dict[str, Any]] = {}
    method_bytes: dict[int, bytes] = {}
    for row in contract["methods"]:
        index = int(row["index"])
        if index in methods:
            raise DynamicSystemRoutingError(f"duplicate route method index {index}")
        image.validate_method_row([index, row["type"], row["method"], int(row["rva"])], label="dynamic_system_routing")
        method = image.metadata.methods[index]
        parameters = [image.metadata.metadata_type_name(p.type_index) for p in image.metadata.parameters_for(method)]
        return_type = image.metadata.metadata_type_name(method.return_type)
        if parameters != row["parameters"] or return_type != row["returnType"]:
            raise DynamicSystemRoutingError(f"route method signature differs: {row['method']}")
        raw = image.pe.bytes_at_va(image.pe.image_base + int(row["rva"]), int(row["bodyExtent"]))
        if hashlib.sha256(raw).hexdigest().upper() != row["bodySha256"].upper():
            raise DynamicSystemRoutingError(f"route method body differs: {row['method']}")
        methods[index] = row
        method_bytes[index] = raw
    if set(methods) != {
        int(layout["systemTypeMethodIndex"]),
        int(layout["systemLookupMethodIndex"]),
        int(layout["getSystemMethodIndex"]),
    }:
        raise DynamicSystemRoutingError("route method set differs")
    expected = (
        ("systemTypeMethodIndex", "GetSystemTypeByDataType", layout["systemEnumType"], [layout["dataEnumType"]]),
        ("systemLookupMethodIndex", "GetSystemByDataType", "Beyond.Gameplay.Core.DynamicScene.DynamicSceneSystemBase", [layout["dataEnumType"]]),
        ("getSystemMethodIndex", "GetSystem", "Beyond.Gameplay.Core.DynamicScene.DynamicSceneSystemBase", [layout["systemEnumType"]]),
    )
    for key, name, result_type, parameters in expected:
        row = methods[int(layout[key])]
        if (row["type"], row["method"], row["returnType"], row["parameters"]) != (
            layout["sceneType"], name, result_type, parameters,
        ):
            raise DynamicSystemRoutingError(f"selected route method binding differs: {name}")
    lookup = methods[int(layout["systemLookupMethodIndex"])]
    raw_lookup = method_bytes[lookup["index"]]
    if _rel_call_target(raw_lookup, b"\x8b\xd3\xe8", int(lookup["rva"]), "GetSystemByDataType route") != int(layout["calledRoute"]["rva"]):
        raise DynamicSystemRoutingError("GetSystemByDataType does not call reviewed route")
    get_system = methods[int(layout["getSystemMethodIndex"])]
    if _rel_call_target(raw_lookup, b"\x8a\xd0\x48\x8b\xcf\xe8", int(lookup["rva"]), "GetSystemByDataType system lookup") != int(get_system["rva"]):
        raise DynamicSystemRoutingError("GetSystemByDataType does not call GetSystem")
    routes, _shape = _called_route(image, layout["calledRoute"], sorted(data_enum))
    switch = methods[int(layout["systemTypeMethodIndex"])]
    for data_id, system_id in routes.items():
        actual = _registered_switch(method_bytes[switch["index"]], data_id)
        if actual != system_id:
            raise DynamicSystemRoutingError(
                f"Type={data_id}: called route={system_id} registered switch={actual}"
            )
        if system_id not in system_enum:
            raise DynamicSystemRoutingError(f"Type={data_id}: unknown EDynamicSystem value={system_id}")
    return routes, data_enum, system_enum, digest, receipt


def audit_current_routes(
    gameassembly: Path, metadata: Path, *, outer_path: Path, ledger_path: Path,
    cli_path: Path, input_root: Path, expected_input_set_sha256: str,
) -> dict[str, Any]:
    routes, data_enum, system_enum, route_digest, receipt = validate_native_routes(gameassembly, metadata)
    layout, main_layout, index_enum, index_digest, main_digest, index_receipt = validate_data_index_layout(
        gameassembly, metadata,
    )
    if receipt != index_receipt or data_enum != index_enum:
        raise DynamicSystemRoutingError("route and DataIndex contracts use different selected native evidence")
    index_report = audit_data_index_main(
        layout, main_layout, index_enum, outer_path=outer_path, ledger_path=ledger_path,
        cli_path=cli_path, input_root=input_root,
        expected_input_set_sha256=expected_input_set_sha256,
    )
    observed = {row["type"]: row for row in index_report["types"]}
    rows = [
        {
            "type": data_id,
            "dataName": data_name,
            "system": routes[data_id],
            "systemName": system_enum[routes[data_id]],
            "currentRecordCount": observed.get(data_id, {}).get("recordCount", 0),
            "currentPopulatedGrids": observed.get(data_id, {}).get("populatedGrids", 0),
        }
        for data_id, data_name in sorted(data_enum.items())
    ]
    return {
        "format": "endfield.dynamic-system-routing-native-audit.v1",
        "status": "validated",
        "inputSetSha256": index_report["inputSetSha256"],
        "contractSha256": route_digest,
        "dataIndexContractSha256": index_digest,
        "mainVectorContractSha256": main_digest,
        "nativeInputs": receipt,
        "outer": index_report["outer"],
        "corpus": index_report["corpus"],
        "observedTypeCount": len(observed),
        "unroutedObservedTypes": [data_id for data_id in observed if routes[data_id] == 0],
        "routes": rows,
        "evidenceBoundary": "The selected GetSystemByDataType body calls a reviewed native jump table and then GetSystem; an independently registered switch agrees for every EDynamicSceneData member. Current authenticated DataIndex Type codes all have a nonzero system route. A stored record's presence does not prove a runtime lookup or activation.",
    }


def _markdown(report: dict[str, Any]) -> str:
    corpus = report["corpus"]
    rows = "\n".join(
        f"| {row['type']} | `{row['dataName']}` | {row['system']} | `{row['systemName']}` | {row['currentRecordCount']:,} |"
        for row in report["routes"] if row["currentRecordCount"]
    )
    return "\n".join([
        "# DynamicStreaming selected native system routes", "",
        f"- Status: `{report['status']}`; input set: `{report['inputSetSha256']}`.",
        f"- Authenticated DataIndex records: {corpus['validRecords']:,} across {corpus['grids']:,} grids in {corpus['files']:,} files.",
        f"- Observed Type values: {report['observedTypeCount']}; without a system route: {len(report['unroutedObservedTypes'])}.",
        "- The called jump table and independently registered switch agree for every selected data enum member.",
        "- This is a code route and stored-data join, not a runtime activation trace.",
        "", "## Routes used by current DataIndex records", "",
        "| Type | Data name | System | System name | Records |",
        "|---:|---|---:|---|---:|", rows, "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--outer-report", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)
    try:
        report = audit_current_routes(
            args.gameassembly, args.metadata, outer_path=args.outer_report,
            ledger_path=args.ledger, cli_path=args.cli, input_root=args.input_root,
            expected_input_set_sha256=args.expected_input_set_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError, struct.error) as error:
        print(f"dynamic-system-routing-native-audit: {error}", file=sys.stderr)
        return 1
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(
        "DynamicStreaming system route audit passed: "
        f"files={report['corpus']['files']} records={report['corpus']['validRecords']} "
        f"observedTypes={report['observedTypeCount']} unrouted={len(report['unroutedObservedTypes'])}"
    )
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
