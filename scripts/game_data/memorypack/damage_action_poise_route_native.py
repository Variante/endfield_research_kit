"""Audit the selected DamageAction route from a stored Poise calculation.

The result proves a conditional intermediate PoisePackData input. It does not
observe action execution or calculate an applied or displayed Poise amount.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp import protocol as il2cpp
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "damage_action_poise_route_native.json"
SCHEMA = "endfield.damage-action-poise-route-native-contract.v1"
REPORT_SCHEMA = "endfield.damage-action-poise-route-native-audit.v1"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/damage_action_poise_route_native.json"


def _rva(value: str) -> int:
    if not isinstance(value, str) or re.fullmatch(r"0x[0-9a-f]+", value) is None:
        raise ValueError(f"contract-rva={value!r}")
    return int(value, 16)


def _runtime_type(image: NativeImage, index: int) -> str:
    if not 0 <= index < int(image.registration["typesCount"]):
        raise ValueError(f"native-type-index={index}")
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    if not pointer:
        raise ValueError(f"native-type-pointer={index}")
    return il2cpp.runtime_type_name(image.pe, image.metadata, pointer)


def _signature(image: NativeImage, method: Any) -> tuple[list[list[str]], str]:
    return (
        [[image.metadata.string(row.name_index), _runtime_type(image, row.type_index)]
         for row in image.metadata.parameters_for(method)],
        _runtime_type(image, method.return_type),
    )


def _relative_target(image: NativeImage, site: int, opcode: bytes, width: int) -> int:
    if width not in (1, 4):
        raise ValueError(f"contract-relative-width={width}")
    raw = image.pe.bytes_at_va(image.pe.image_base + site, len(opcode) + width)
    if raw[:len(opcode)] != opcode:
        raise ValueError(f"native-opcode={site:#x}:expected={opcode.hex()}:actual={raw.hex()}")
    delta = struct.unpack_from("<b" if width == 1 else "<i", raw, len(opcode))[0]
    return site + len(raw) + delta


def _validate(image: NativeImage, contract: dict[str, Any]) -> dict[str, Any]:
    methods = contract["methods"]
    if set(methods) != {"processDamage", "patchCheck", "poisePackConstructor", "applyPoiseModifier"}:
        raise ValueError("contract-method-set")
    resolved = {}
    for role, row in methods.items():
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError(f"contract-method-row={role}")
        resolved[role] = _rva(row[3])
        image.validate_method_row([*row[:3], resolved[role]], label="poise-route")

    parameters, return_type = _signature(image, image.metadata.methods[methods["processDamage"][0]])
    if parameters != contract["processDamageParameters"] or return_type != contract["processDamageReturnType"]:
        raise ValueError(f"native-process-damage-signature={parameters!r}:{return_type}")
    modifier_parameters, modifier_return = _signature(
        image, image.metadata.methods[methods["applyPoiseModifier"][0]],
    )
    if modifier_parameters != contract["applyPoiseModifierParameters"] or modifier_return != "void":
        raise ValueError(f"native-poise-modifier-signature={modifier_parameters!r}:{modifier_return}")

    expected_fields = contract["fields"]
    if len(expected_fields) != 4 or [row[1] for row in expected_fields] != [
        "damageUnits", "poiseCalculation", "calcResult", "value",
    ]:
        raise ValueError("contract-field-set")
    checked_fields = []
    for owner_name, field_name, expected_type, expected_offset, expected_token in expected_fields:
        owners = [row for row in image.metadata.types
                  if image.metadata.type_full_name(row) == owner_name]
        if len(owners) != 1:
            raise ValueError(f"native-field-owner={owner_name}:{len(owners)}")
        owner = owners[0]
        fields = [row for row in image.metadata.fields_for(owner)
                  if image.metadata.string(row.name_index) == field_name]
        if len(fields) != 1:
            raise ValueError(f"native-field-count={owner_name}.{field_name}:{len(fields)}")
        field = fields[0]
        actual_offset = il2cpp.runtime_type_field_offsets(
            image.metadata, image.pe, image.registration, owner.index,
        ).get(field_name)
        actual_type = _runtime_type(image, field.type_index)
        if (actual_offset != expected_offset or actual_type != expected_type
                or f"0x{field.token:08x}" != expected_token):
            raise ValueError(
                f"native-field={owner_name}.{field_name}:type={actual_type}:offset={actual_offset}"
            )
        checked_fields.append({"owner": owner_name, "name": field_name,
                               "type": actual_type, "offset": actual_offset})

    enum_type, enum_name, enum_id, enum_token = contract["beforeCalculationEnum"]
    members = il2cpp.native_enum_members(
        image.metadata, il2cpp.field_defaults(image.metadata),
        image.pe, image.registration, enum_type,
    )
    matching = [row for row in members if row["name"] == enum_name]
    if len(matching) != 1 or matching[0]["id"] != enum_id or matching[0]["token"] != enum_token:
        raise ValueError(f"native-poise-timing-enum={enum_type}.{enum_name}")

    pdata = image.mapper.pdata_function_extents(image.pe)
    actual_end = pdata.get(image.pe.image_base + resolved["processDamage"])
    if actual_end != image.pe.image_base + _rva(contract["processDamagePdataEndRva"]):
        raise ValueError(f"native-process-damage-pdata-end={actual_end!r}")
    helper_rva = _rva(contract["dispatchHelperRva"])
    helper_end_rva = _rva(contract["dispatchHelperPdataEndRva"])
    if pdata.get(image.pe.image_base + helper_rva) != image.pe.image_base + helper_end_rva:
        raise ValueError("native-dispatch-helper-pdata-end")
    windows = contract["codeWindows"]
    if len(windows) != 8:
        raise ValueError("contract-code-window-count")
    parsed_windows = [
        {**row, "startRva": _rva(row["startRva"]), "endRva": _rva(row["endRva"])}
        for row in windows
    ]
    if any(row["startRva"] >= row["endRva"] for row in parsed_windows):
        raise ValueError("contract-code-window-range")
    if (any(row["startRva"] < resolved["processDamage"]
            or row["endRva"] > _rva(contract["processDamagePdataEndRva"])
            for row in parsed_windows[:-1])
            or parsed_windows[-1]["startRva"] != helper_rva
            or parsed_windows[-1]["endRva"] != helper_end_rva):
        raise ValueError("contract-code-window-owner")
    image.check_windows(parsed_windows, label="poise-route")

    witnesses = contract["instructionWindows"]
    if set(witnesses) != {
        "listField", "indexedUnitStore", "savedUnitLoad", "nonnullPoiseGuard",
        "beforeCalculationTiming", "poisePackBase", "poiseCalcLoad", "dispatchOperand",
        "returnValue", "packValueMove", "packValueStore", "helperIndirectCall",
        "helperIndirectReturn", "helperReturn",
    }:
        raise ValueError("contract-instruction-window-set")
    image.check_instruction_windows(
        [[_rva(row[0]), row[1], row[2]] for row in witnesses.values()],
        label="poise-route",
    )
    # Decode only the reviewed displacement carriers needed for the field join.
    raw = {key: bytes.fromhex(row[1]) for key, row in witnesses.items()}
    if (raw["listField"][:3] != b"\x48\x8b\x5b"
            or raw["listField"][3] != checked_fields[0]["offset"]
            or raw["nonnullPoiseGuard"][:3] != b"\x49\x83\x7d"
            or raw["nonnullPoiseGuard"][3] != checked_fields[1]["offset"]
            or raw["poiseCalcLoad"][:3] != b"\x49\x8b\x5d"
            or raw["poiseCalcLoad"][3] != checked_fields[1]["offset"]):
        raise ValueError("native-poise-field-displacements")
    if (raw["indexedUnitStore"][:4] != b"\x48\x89\x84\x24"
            or raw["savedUnitLoad"][:4] != b"\x4c\x8b\xac\x24"
            or raw["indexedUnitStore"][4:] != raw["savedUnitLoad"][4:]):
        raise ValueError("native-indexed-unit-stack-join")
    if (raw["beforeCalculationTiming"][:1] != b"\xba"
            or struct.unpack_from("<I", raw["beforeCalculationTiming"], 1)[0] != enum_id):
        raise ValueError("native-poise-timing-operand")
    if (raw["poisePackBase"][:4] != b"\x48\x8d\x8c\x24"
            or raw["packValueStore"][:4] != b"\x0f\x29\x84\x24"
            or (struct.unpack_from("<I", raw["packValueStore"], 4)[0]
                - struct.unpack_from("<I", raw["poisePackBase"], 4)[0]
                != checked_fields[2]["offset"] - 16)
            or checked_fields[3]["offset"] != 16):
        raise ValueError("native-poise-pack-result-slot")

    calls = contract["callTargets"]
    if len(calls) != 7 or sum(
        role == contract["dispatchHelperRva"] for _, role in calls
    ) != 1:
        raise ValueError("contract-call-count")
    for site_text, role in calls:
        site = _rva(site_text)
        actual = _relative_target(image, site, b"\xe8", 4)
        expected = _rva(role) if role.startswith("0x") else resolved[role]
        if actual != expected:
            raise ValueError(f"native-call-target={site:#x}:actual={actual:#x}")
    branches = contract["branchTargets"]
    if len(branches) != 3:
        raise ValueError("contract-branch-count")
    for site_text, opcode, width, target_text in branches:
        site = _rva(site_text)
        actual = _relative_target(image, site, bytes.fromhex(opcode), width)
        if actual != _rva(target_text):
            raise ValueError(f"native-branch-target={site:#x}:actual={actual:#x}")
    return {
        "method": methods["processDamage"],
        "processDamageParameters": parameters,
        "fields": checked_fields,
        "beforeCalculationEnum": matching[0],
        "processDamagePdataEndRva": contract["processDamagePdataEndRva"],
        "dispatchHelperPdataEndRva": contract["dispatchHelperPdataEndRva"],
        "codeWindows": [{key: row[key] for key in ("startRva", "endRva", "sha256")}
                        for row in windows],
        "instructionWitnesses": len(witnesses),
        "callSites": len(calls), "branchSites": len(branches),
    }


def audit(*, gameassembly: Path, metadata: Path,
          contract_path: Path = CONTRACT) -> dict[str, Any]:
    contract, digest = read_reviewed_contract(
        contract_path, schema=SCHEMA, status="validated", label="poise-route",
    )
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["gameAssemblySha256"], expected["metadataSha256"],
        gameassembly=gameassembly, metadata=metadata,
    )
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA, "status": gate.status, "detail": gate.detail,
        "contractSha256": digest,
        "nativeInputs": {"gameAssemblySha256": gate.gameassembly_sha256,
                         "metadataSha256": gate.metadata_sha256},
        "evidenceBoundary": contract["evidenceBoundary"],
    }
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return report
    try:
        report.update(_validate(NativeImage(gameassembly, metadata, label="poise-route"), contract))
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
