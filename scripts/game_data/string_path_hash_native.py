"""Authenticate the selected StringPathHash hash-routing and lookup methods.

The native contract records byte-checked method bodies and direct callsites.
This validator proves the selected build's path-prefix branch and hash
forwarders. Corpus output comparison is a separate check; these static bytes
alone do not prove which inputs were used to write every stored catalog row.
"""

from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run as: python -m scripts.game_data.string_path_hash_native")

import argparse
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import literal_record, unresolved_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name


CONTRACT = CONTRACTS_DIR / "string_path_hash_native.json"
SCHEMA = "endfield.string-path-hash-native-contract.v1"
AUDIT_SCHEMA = "endfield.string-path-hash-native-audit.v1"


def _require(ok: bool, name: str) -> None:
    if not ok:
        raise ValueError(f"string-path-hash-native:{name}")


def _bytes(image: Any, rva: int, size: int) -> bytes:
    return image.pe.bytes_at_va(image.pe.image_base + rva, size)


def _relative_target(image: Any, rva: int, opcode: int) -> int:
    raw = _bytes(image, rva, 5)
    _require(raw[0] == opcode, f"relative-opcode:{rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def _literal_at(image: Any, rva: int) -> str:
    instruction = _bytes(image, rva, 7)
    _require(instruction[:3] == b"\x48\x8b\x15", "qualifier-literal-load")
    cell_rva = rva + 7 + struct.unpack_from("<i", instruction, 3)[0]
    section = image.metadata.sections["stringLiteral"]
    data_section = image.metadata.sections["stringLiteralData"]
    cell = _bytes(image, cell_rva, 8)
    index = unresolved_usage_index(
        cell, section.size // 8, tag=5, source=str(image.gameassembly), offset=cell_rva
    )
    start, length = literal_record(
        image.metadata.buf[section.offset + index * 8:section.offset + (index + 1) * 8],
        data_section.size, source=str(image.metadata_path), offset=section.offset + index * 8,
    )
    return image.metadata.buf[data_section.offset + start:data_section.offset + start + length].decode("utf-8")


def _check_native(image: Any, contract: dict[str, Any]) -> dict[str, Any]:
    value = contract["hashValueType"]
    _require(image.type_name(value["index"]) == value["name"], "hash-type")
    fields = runtime_type_field_offsets(image.metadata, image.pe, image.registration, value["index"])
    _require(fields.get(value["field"]) == value["boxedFieldOffset"], "hash-field-offset")
    selected = [
        field for field in image.metadata.fields_for(image.metadata.types[value["index"]])
        if image.metadata.string(field.name_index) == value["field"]
    ]
    _require(len(selected) == 1, "hash-field-selection")
    type_va = image.pe.u64_at_va(int(image.registration["types"], 16) + selected[0].type_index * 8)
    _require(runtime_type_name(image.pe, image.metadata, type_va) == value["fieldType"], "hash-field-type")

    for row in contract["methods"]:
        image.validate_method_row(row, label="string-path-hash-native")
    image.check_windows(contract["codeWindows"], label="string-path-hash-native")

    qualifier = contract["qualifier"]
    starts = image.metadata.methods[qualifier["startsWithMethodIndex"]]
    parameters = [image.metadata.metadata_type_name(p.type_index)
                  for p in image.metadata.parameters_for(starts)]
    _require(parameters == ["System.String", "System.StringComparison"], "starts-with-signature")
    _require(_literal_at(image, qualifier["literalLoadRva"]) == qualifier["literal"],
             "prefix-literal")
    _require(_bytes(image, qualifier["comparisonInstructionRva"], 6)
             == b"\x41\xb8" + struct.pack("<I", qualifier["comparisonEnumValue"]),
             "prefix-comparison-enum")
    for source, target in contract["callEdges"]:
        _require(_relative_target(image, source, 0xE8) == target, f"call:{source:#x}")
    for source, target in contract["jumpEdges"]:
        _require(_relative_target(image, source, 0xE9) == target, f"jump:{source:#x}")
    for rva, expected_hex, label in contract["instructionBytes"]:
        expected = bytes.fromhex(expected_hex)
        _require(_bytes(image, rva, len(expected)) == expected, f"instruction:{label}")

    return {
        "methodCount": len(contract["methods"]),
        "codeWindowCount": len(contract["codeWindows"]),
        "directCallCount": len(contract["callEdges"]),
        "directJumpCount": len(contract["jumpEdges"]),
        "prefixLiteral": qualifier["literal"],
        "prefixComparisonEnumValue": qualifier["comparisonEnumValue"],
        "hashValueField": value["field"],
        "hashValueFieldType": value["fieldType"],
        "semanticLimits": contract["semanticLimits"],
    }


def audit_string_path_hash_native(
    *, contract_path: Path = CONTRACT, gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    contract, contract_sha = read_reviewed_contract(
        contract_path, schema=SCHEMA, label="string-path-hash-native", status="validated"
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
        report.update(status="mismatched", detail="UnityPlayer.dll hash differs from reviewed contract")
        return report
    try:
        image = open_native_image(gate.gameassembly, gate.metadata)
        report["route"] = _check_native(image, contract)
    except (ValueError, RuntimeError, KeyError, IndexError, struct.error) as error:
        report.update(status="mismatched", detail=f"native proof failed: {error}")
        return report
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = audit_string_path_hash_native(
        contract_path=args.contract, gameassembly=args.gameassembly, metadata=args.metadata
    )
    result = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result, encoding="utf-8")
    print(result, end="")
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
