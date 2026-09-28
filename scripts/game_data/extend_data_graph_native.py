"""Authenticate the selected native archive-to-Graph index route.

This proves static direct reads and calls under the selected binary inputs.
It does not witness a graph instance, runtime execution, or an owner key.
"""

from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run as: python -m scripts.game_data.extend_data_graph_native")

import argparse
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import (
    literal_record, rip_qword_load_target, unresolved_usage_index,
)
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name


CONTRACT = CONTRACTS_DIR / "extend_data_graph_native.json"
SCHEMA = "endfield.extend-data-graph-native-contract.v1"
AUDIT_SCHEMA = "endfield.extend-data-graph-native-audit.v1"


def _require(ok: bool, detail: str) -> None:
    if not ok:
        raise ValueError(f"extend-data-graph-native:{detail}")


def _relative_call_target(image: Any, rva: int) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    _require(raw[0] == 0xE8, f"call-opcode:{rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def _selected_literal(image: Any, row: dict[str, Any]) -> str:
    rva = row["loadRva"]
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 7)
    cell_va = rip_qword_load_target(raw, image.pe.image_base + rva,
                                   source=str(image.gameassembly))
    _require(cell_va - image.pe.image_base == row["usageCellRva"], "literal-cell-rva")
    section = image.metadata.sections["stringLiteral"]
    data = image.metadata.sections["stringLiteralData"]
    index = unresolved_usage_index(
        image.pe.bytes_at_va(cell_va, 8), section.size // 8,
        tag=5, source=str(image.gameassembly), offset=cell_va,
    )
    _require(index == row["literalIndex"], "literal-index")
    at = section.offset + index * 8
    start, size = literal_record(
        image.metadata.buf[at:at + 8], data.size,
        source=str(image.metadata_path), offset=at,
    )
    text = image.metadata.buf[data.offset + start:data.offset + start + size].decode("utf-8")
    _require(text == row["text"], "archive-path-literal")
    return text


def _check_native(image: Any, contract: dict[str, Any]) -> dict[str, Any]:
    for typ in contract["types"]:
        _require(image.type_name(typ["index"]) == typ["name"], f"type:{typ['index']}")
        fields = runtime_type_field_offsets(
            image.metadata, image.pe, image.registration, typ["index"]
        )
        definitions = {
            image.metadata.string(field.name_index): field
            for field in image.metadata.fields_for(image.metadata.types[typ["index"]])
        }
        for name, offset, field_type in typ["fields"]:
            _require(fields.get(name) == offset, f"field-offset:{typ['name']}.{name}")
            _require(name in definitions, f"field-declaration:{typ['name']}.{name}")
            pointer = image.pe.u64_at_va(
                int(image.registration["types"], 16) + definitions[name].type_index * 8
            )
            _require(runtime_type_name(image.pe, image.metadata, pointer) == field_type,
                     f"field-type:{typ['name']}.{name}")
    type_indices = {typ["name"]: typ["index"] for typ in contract["types"]}
    graph_type = image.metadata.types[type_indices["NodeCanvas.Framework.Graph"]]
    behaviour_type = image.metadata.types[type_indices["NodeCanvas.BehaviourTrees.BehaviourTree"]]
    _require(behaviour_type.parent_index == graph_type.byval_type_index,
             "behaviour-tree-inherits-graph")
    for row in contract["methods"]:
        image.validate_method_row(row, label="extend-data-graph-native")
    parameter = contract["methodParameter"]
    method = image.metadata.methods[parameter["methodIndex"]]
    params = list(image.metadata.parameters_for(method))
    _require(len(params) == 1, "indexed-string-parameter-count")
    _require(image.metadata.string(params[0].name_index) == parameter["parameterName"],
             "indexed-string-parameter-name")
    _require(image.metadata.metadata_type_name(params[0].type_index)
             == parameter["parameterType"], "indexed-string-parameter-type")
    image.check_windows(contract["codeWindows"], label="extend-data-graph-native")
    image.check_instruction_windows(contract["instructionWindows"], label="extend-data-graph-native")
    literal = _selected_literal(image, contract["pathLiteral"])
    for source, target in contract["directCalls"]:
        _require(_relative_call_target(image, source) == target, f"call:{source:#x}")
    return {
        "archivePath": literal,
        "graphIndexField": "NodeCanvas.Framework.Graph._serializedGraphStringIndex",
        "graphCompressionFlag": "NodeCanvas.Framework.Graph._enableGraphStringCompress",
        "graphSubclass": "NodeCanvas.BehaviourTrees.BehaviourTree",
        "methodCount": len(contract["methods"]),
        "codeWindowCount": len(contract["codeWindows"]),
        "instructionWindowCount": len(contract["instructionWindows"]),
        "directCallCount": len(contract["directCalls"]),
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def audit_extend_data_graph_native(
    *, contract_path: Path = CONTRACT, gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    contract, contract_sha = read_reviewed_contract(
        contract_path, schema=SCHEMA, label="extend-data-graph-native", status="validated"
    )
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["globalMetadataSha256"],
        gameassembly=gameassembly, metadata=metadata,
    )
    report: dict[str, Any] = {
        "schema": AUDIT_SCHEMA, "status": gate.status, "detail": gate.detail,
        "contractSha256": contract_sha,
        "nativeInputs": {
            "gameAssemblySha256": gate.gameassembly_sha256,
            "globalMetadataSha256": gate.metadata_sha256,
        },
    }
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return report
    unity = gate.gameassembly.with_name("UnityPlayer.dll")
    if not unity.is_file():
        report.update(status="missing", detail=f"UnityPlayer.dll missing at {unity}")
        return report
    unity_sha = sha256_file(unity).upper()
    report["nativeInputs"]["unityPlayerSha256"] = unity_sha
    if unity_sha != inputs["unityPlayerSha256"].upper():
        report.update(status="mismatched", detail="UnityPlayer.dll hash differs")
        return report
    try:
        image = open_native_image(gate.gameassembly, gate.metadata)
        report["route"] = _check_native(image, contract)
    except (ValueError, RuntimeError, KeyError, IndexError, struct.error, UnicodeError) as error:
        report.update(status="mismatched", detail=f"native proof failed: {error}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = audit_extend_data_graph_native(
        contract_path=args.contract, gameassembly=args.gameassembly, metadata=args.metadata
    )
    result = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result, encoding="utf-8")
    print(result, end="")
    return 0 if report["status"] == NATIVE_EVIDENCE_VALIDATED else 1


if __name__ == "__main__":
    raise SystemExit(main())
