"""Validate the selected native AtkScaleCalculation.Evaluate proof.

The reviewed contract binds its signature, operands and arithmetic to exact
selected-build bytes. The claim covers normally returning nonpatch paths, not
an observed DamageUnit invocation or final damage.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp import protocol as il2cpp
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "atk_scale_calculation_native.json"
SCHEMA = "endfield.atk-scale-calculation-native-contract.v1"
REPORT_SCHEMA = "endfield.atk-scale-calculation-native-audit.v1"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/atk_scale_calculation_native.json"


def _rva(value: str) -> int:
    if not isinstance(value, str) or re.fullmatch(r"0x[0-9a-f]+", value) is None:
        raise ValueError(f"invalid-rva={value!r}")
    return int(value, 16)


def _relative_target(image: NativeImage, site_rva: int, opcode: bytes, width: int) -> int:
    if width not in (1, 4):
        raise ValueError(f"invalid-relative-width={width}")
    raw = image.pe.bytes_at_va(image.pe.image_base + site_rva, len(opcode) + width)
    if raw[:len(opcode)] != opcode:
        raise ValueError(f"native-opcode={site_rva:#x}:expected={opcode.hex()}:actual={raw.hex()}")
    delta = struct.unpack_from("<b" if width == 1 else "<i", raw, len(opcode))[0]
    return site_rva + len(raw) + delta


def _runtime_type(image: NativeImage, index: int) -> str:
    registration = image.registration
    type_count = int(registration["typesCount"])
    if not 0 <= index < type_count:
        raise ValueError(f"native-type-index={index}")
    type_table = int(registration["types"], 16)
    type_va = image.pe.u64_at_va(type_table + index * 8)
    if not type_va:
        raise ValueError(f"native-type-pointer={index}")
    return il2cpp.runtime_type_name(image.pe, image.metadata, type_va)


def _one_type(image: NativeImage, name: str) -> Any:
    found = [row for row in image.metadata.types
             if image.metadata.type_full_name(row) == name]
    if len(found) != 1:
        raise ValueError(f"native-type-count={name}:{len(found)}")
    return found[0]


def _one_field(image: NativeImage, owner: Any, name: str) -> Any:
    found = [row for row in image.metadata.fields_for(owner)
             if image.metadata.string(row.name_index) == name]
    if len(found) != 1:
        raise ValueError(f"native-field-count={image.metadata.type_full_name(owner)}.{name}:{len(found)}")
    return found[0]


def _validate_body(image: NativeImage, contract: dict[str, Any]) -> dict[str, Any]:
    methods = contract["methods"]
    if set(methods) != {"evaluate", "blackboardValue", "getAtk", "patchCheck"}:
        raise ValueError("contract-method-set")
    resolved: dict[str, int] = {}
    method_rows: list[dict[str, Any]] = []
    for key, row in methods.items():
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError(f"contract-method-row={key}")
        selected = [row[0], row[1], row[2], _rva(row[3])]
        image.validate_method_row(selected, label="atk-scale")
        resolved[key] = selected[3]
        method_rows.append({"role": key, "index": row[0], "type": row[1],
                            "method": row[2], "pointerRva": row[3]})

    evaluate = image.metadata.methods[methods["evaluate"][0]]
    actual_parameters = [
        [image.metadata.string(row.name_index), _runtime_type(image, row.type_index)]
        for row in image.metadata.parameters_for(evaluate)
    ]
    if actual_parameters != contract["evaluateParameters"]:
        raise ValueError(f"native-evaluate-parameters={actual_parameters!r}")
    result_type = _runtime_type(image, evaluate.return_type)
    if result_type != contract["evaluateReturnType"]:
        raise ValueError(f"native-evaluate-return={result_type}")
    callee_signatures = contract["calleeSignatures"]
    if set(callee_signatures) != {"blackboardValue", "getAtk"}:
        raise ValueError("contract-callee-signature-set")
    for key, selected in callee_signatures.items():
        method = image.metadata.methods[methods[key][0]]
        actual = [
            [image.metadata.string(row.name_index), _runtime_type(image, row.type_index)]
            for row in image.metadata.parameters_for(method)
        ]
        return_type = _runtime_type(image, method.return_type)
        if actual != selected["parameters"] or return_type != selected["returnType"]:
            raise ValueError(f"native-callee-signature={key}:parameters={actual!r}:return={return_type}")

    owner_name = contract["ownerType"]
    owner = _one_type(image, owner_name)
    selected_field = contract["field"]
    field = _one_field(image, owner, selected_field["name"])
    offsets = il2cpp.runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, owner.index,
    )
    if offsets.get(selected_field["name"]) != selected_field["offset"]:
        raise ValueError(f"native-field-offset={owner_name}.{selected_field['name']}")
    if f"0x{field.token:08x}" != selected_field["token"]:
        raise ValueError(f"native-field-token={owner_name}.{selected_field['name']}")
    field_type = _runtime_type(image, field.type_index)
    if field_type != selected_field["type"]:
        raise ValueError(f"native-field-type={owner_name}.{selected_field['name']}:{field_type}")

    result_owner_name, result_field_name, result_field_type, result_field_token = contract["resultValueField"]
    result_owner = _one_type(image, result_owner_name)
    result_field = _one_field(image, result_owner, result_field_name)
    if (_runtime_type(image, result_field.type_index) != result_field_type
            or f"0x{result_field.token:08x}" != result_field_token):
        raise ValueError(f"native-result-value-field={result_owner_name}.{result_field_name}")

    enum_spec = contract["overrideIndexEnumMember"]
    members = il2cpp.native_enum_members(
        image.metadata, il2cpp.field_defaults(image.metadata),
        image.pe, image.registration, enum_spec["type"],
    )
    selected_enum = [row for row in members if row["name"] == enum_spec["member"]]
    if len(selected_enum) != 1 or selected_enum[0]["id"] != enum_spec["id"] or selected_enum[0]["token"] != enum_spec["token"]:
        raise ValueError(f"native-override-index-enum={enum_spec['type']}.{enum_spec['member']}")

    windows = contract["codeWindows"]
    if len(windows) != 3:
        raise ValueError("contract-code-window-count")
    image.check_windows([
        {**row, "startRva": _rva(row["startRva"]), "endRva": _rva(row["endRva"])}
        for row in windows
    ], label="atk-scale")
    witnesses = contract["instructionWindows"]
    if len(witnesses) != 4:
        raise ValueError("contract-instruction-window-count")
    image.check_instruction_windows(
        [[_rva(row[0]), row[1], row[2]] for row in witnesses],
        label="atk-scale",
    )
    calls = contract["calls"]
    if len(calls) != 3:
        raise ValueError("contract-call-count")
    for call in calls:
        site = _rva(call["siteRva"])
        target = _relative_target(image, site, b"\xe8", 4)
        if target != resolved[call["method"]]:
            raise ValueError(f"native-call-target={site:#x}:actual={target:#x}")
    branches = contract["branches"]
    if len(branches) != 6:
        raise ValueError("contract-branch-count")
    for branch in branches:
        site = _rva(branch["siteRva"])
        target = _relative_target(
            image, site, bytes.fromhex(branch["opcode"]), branch["displacementBytes"],
        )
        if target != _rva(branch["targetRva"]):
            raise ValueError(f"native-branch-target={site:#x}:actual={target:#x}")
    return {
        "methods": method_rows,
        "evaluateParameters": actual_parameters,
        "evaluateReturnType": result_type,
        "field": {"name": selected_field["name"], "type": field_type,
                  "offset": offsets[selected_field["name"]], "token": selected_field["token"]},
        "overrideIndexEnumMember": selected_enum[0],
        "codeWindows": [{"startRva": row["startRva"], "endRva": row["endRva"],
                         "sha256": row["sha256"]} for row in windows],
        "callSites": len(calls), "branches": len(branches),
    }


def audit(*, gameassembly: Path, metadata: Path, contract_path: Path = CONTRACT) -> dict[str, Any]:
    contract, digest = read_reviewed_contract(
        contract_path, schema=SCHEMA, label="atk-scale", status="validated",
    )
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["gameAssemblySha256"], expected["metadataSha256"],
        gameassembly=gameassembly, metadata=metadata,
    )
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "status": gate.status,
        "detail": gate.detail,
        "contractSha256": digest,
        "nativeInputs": {
            "gameAssemblySha256": gate.gameassembly_sha256,
            "metadataSha256": gate.metadata_sha256,
        },
        "evidenceBoundary": contract["evidenceBoundary"],
    }
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return report
    image = NativeImage(gameassembly, metadata, label="atk-scale")
    try:
        report.update(_validate_body(image, contract))
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, struct.error) as error:
        report["status"] = "mismatched"
        report["detail"] = str(error)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if (REPO_ROOT / "reports").resolve() not in output.parents:
        parser.error("--output must be under reports/")
    try:
        report = audit(gameassembly=args.gameassembly, metadata=args.metadata)
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, TypeError) as error:
        report = {"schema": REPORT_SCHEMA, "status": "failed", "detail": str(error)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "detail": report.get("detail", ""),
                      "output": str(output)}, sort_keys=True))
    return 0 if report["status"] == NATIVE_EVIDENCE_VALIDATED else 2


if __name__ == "__main__":
    raise SystemExit(main())
