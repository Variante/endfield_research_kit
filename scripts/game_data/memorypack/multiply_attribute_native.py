"""Validate the selected native MultiplyAttributeCalculation.Evaluate proof.

The contract pins one installed IL2CPP pair. Its windows and call/branch sites
were reviewed together as one data-flow claim. This is a static, nonpatch
method-body proof, not an observation that a DamageUnit executed.
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


CONTRACT = CONTRACTS_DIR / "multiply_attribute_calculation_native.json"
SCHEMA = "endfield.multiply-attribute-calculation-native-contract.v1"
REPORT_SCHEMA = "endfield.multiply-attribute-calculation-native-audit.v1"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/multiply_attribute_calculation_native.json"


def _rva(value: str) -> int:
    if not isinstance(value, str) or re.fullmatch(r"0x[0-9a-f]+", value) is None:
        raise ValueError(f"invalid-rva={value!r}")
    return int(value, 16)


def _relative_target(image: NativeImage, site_rva: int, opcode: bytes) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + site_rva, len(opcode) + 4)
    if raw[:len(opcode)] != opcode:
        raise ValueError(f"native-opcode={site_rva:#x}:expected={opcode.hex()}:actual={raw.hex()}")
    delta = struct.unpack_from("<i", raw, len(opcode))[0]
    return site_rva + len(raw) + delta


def _validate_body(image: NativeImage, contract: dict[str, Any]) -> dict[str, Any]:
    methods = contract["methods"]
    if set(methods) != {"evaluate", "getAttribute", "blackboardValue", "patchCheck"}:
        raise ValueError("contract-method-set")
    resolved: dict[str, int] = {}
    method_rows: list[dict[str, Any]] = []
    for key, row in methods.items():
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError(f"contract-method-row={key}")
        selected = [row[0], row[1], row[2], _rva(row[3])]
        image.validate_method_row(selected, label="multiply-attribute")
        resolved[key] = selected[3]
        method_rows.append({"role": key, "index": row[0], "type": row[1],
                            "method": row[2], "pointerRva": row[3]})

    owner_name = contract["ownerType"]
    owners = [row for row in image.metadata.types
              if image.metadata.type_full_name(row) == owner_name]
    if len(owners) != 1:
        raise ValueError(f"native-owner-type-count={owner_name}:{len(owners)}")
    owner = owners[0]
    offsets = il2cpp.runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, owner.index,
    )
    runtime_fields = list(image.metadata.fields_for(owner))
    expected_fields = contract["fields"]
    if len(expected_fields) != 4 or {row["name"] for row in expected_fields} != {
        "valueSource", "attributeType", "multiplier", "addition"
    }:
        raise ValueError("contract-field-set")
    type_table = int(image.registration["types"], 16)
    type_count = int(image.registration["typesCount"])
    field_rows: list[dict[str, Any]] = []
    for selected in expected_fields:
        name = selected["name"]
        found = [row for row in runtime_fields
                 if image.metadata.string(row.name_index) == name]
        if len(found) != 1 or offsets.get(name) != selected["offset"]:
            raise ValueError(f"native-field-offset={owner_name}.{name}")
        field = found[0]
        if f"0x{field.token:08x}" != selected["token"]:
            raise ValueError(f"native-field-token={owner_name}.{name}")
        if not 0 <= field.type_index < type_count:
            raise ValueError(f"native-field-type-index={owner_name}.{name}")
        type_va = image.pe.u64_at_va(type_table + field.type_index * 8)
        if not type_va:
            raise ValueError(f"native-field-type-pointer={owner_name}.{name}")
        actual_type = il2cpp.runtime_type_name(image.pe, image.metadata, type_va)
        if actual_type != selected["type"]:
            raise ValueError(f"native-field-type={owner_name}.{name}:actual={actual_type}")
        field_rows.append({"name": name, "type": actual_type,
                           "offset": offsets[name], "token": selected["token"]})

    enum_spec = contract["valueSourceEnum"]
    enum_rows = il2cpp.native_enum_members(
        image.metadata, il2cpp.field_defaults(image.metadata),
        image.pe, image.registration, enum_spec["type"],
    )
    actual_members = {row["name"]: row["id"] for row in enum_rows}
    if (len(actual_members) != len(enum_rows)
            or len({row["id"] for row in enum_rows}) != len(enum_rows)
            or actual_members != enum_spec["members"]):
        raise ValueError(f"native-value-source-enum:actual={actual_members!r}")

    windows = contract["codeWindows"]
    if len(windows) != 2:
        raise ValueError("contract-code-window-count")
    image.check_windows([
        {**row, "startRva": _rva(row["startRva"]), "endRva": _rva(row["endRva"])}
        for row in windows
    ], label="multiply-attribute")
    witnesses = contract["instructionWindows"]
    if len(witnesses) != 6:
        raise ValueError("contract-instruction-window-count")
    image.check_instruction_windows(
        [[_rva(row[0]), row[1], row[2]] for row in witnesses],
        label="multiply-attribute",
    )
    calls = contract["calls"]
    if len(calls) != 4:
        raise ValueError("contract-call-count")
    for call in calls:
        site = _rva(call["siteRva"])
        target = _relative_target(image, site, b"\xe8")
        if target != resolved[call["method"]]:
            raise ValueError(f"native-call-target={site:#x}:actual={target:#x}")
    branches = contract["branches"]
    if len(branches) != 3:
        raise ValueError("contract-branch-count")
    for branch in branches:
        site = _rva(branch["siteRva"])
        target = _relative_target(image, site, bytes.fromhex(branch["opcode"]))
        if target != _rva(branch["targetRva"]):
            raise ValueError(f"native-branch-target={site:#x}:actual={target:#x}")
    return {
        "methods": method_rows,
        "fields": field_rows,
        "valueSourceEnum": actual_members,
        "codeWindows": [{"startRva": row["startRva"], "endRva": row["endRva"],
                         "sha256": row["sha256"]} for row in windows],
        "callSites": len(calls), "branches": len(branches),
    }


def audit(*, gameassembly: Path, metadata: Path, contract_path: Path = CONTRACT) -> dict[str, Any]:
    contract, digest = read_reviewed_contract(
        contract_path, schema=SCHEMA, label="multiply-attribute", status="validated",
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
    image = NativeImage(gameassembly, metadata, label="multiply-attribute")
    try:
        report.update(_validate_body(image, contract))
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, struct.error) as error:
        report["status"] = "mismatched"
        report["detail"] = str(error)
        return report
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
