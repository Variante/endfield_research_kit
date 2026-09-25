"""Audit the selected normal-entity DamageAction calculation selector.

This authenticates the native branch and simple intermediate expression. It
does not observe a DamageUnit running, a patch choice, or final damage.
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


CONTRACT = CONTRACTS_DIR / "damage_action_normal_route_native.json"
SCHEMA = "endfield.damage-action-normal-route-native-contract.v2"
REPORT_SCHEMA = "endfield.damage-action-normal-route-native-audit.v2"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/damage_action_normal_route_native.json"


def _rva(value: str) -> int:
    if not isinstance(value, str) or re.fullmatch(r"0x[0-9a-f]+", value) is None:
        raise ValueError(f"contract-rva={value!r}")
    return int(value, 16)


def _runtime_type(image: NativeImage, index: int) -> tuple[str, bytes]:
    registration = image.registration
    if not 0 <= index < int(registration["typesCount"]):
        raise ValueError(f"native-type-index={index}")
    pointer = image.pe.u64_at_va(int(registration["types"], 16) + index * 8)
    if pointer == 0:
        raise ValueError(f"native-type-pointer={index}")
    raw = image.pe.bytes_at_va(pointer, 16)
    return il2cpp.runtime_type_name(image.pe, image.metadata, pointer), raw


def _validate(image: NativeImage, contract: dict[str, Any]) -> dict[str, Any]:
    methods = contract["methods"]
    if set(methods) != {"normal", "blackboardValue", "patchCheck",
                        "getAttribute", "getAttributes", "attributeValue"}:
        raise ValueError("contract-method-set")
    resolved: dict[str, int] = {}
    for role, row in methods.items():
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError(f"contract-method-row={role}")
        image.validate_method_row([*row[:3], _rva(row[3])], label="damage-route")
        resolved[role] = _rva(row[3])

    normal = image.metadata.methods[methods["normal"][0]]
    parameters = image.metadata.parameters_for(normal)
    actual = [
        [image.metadata.string(item.name_index), _runtime_type(image, item.type_index)[0]]
        for item in parameters
    ]
    if actual != contract["normalParameters"]:
        raise ValueError(f"native-normal-parameters={actual!r}")
    return_type = _runtime_type(image, normal.return_type)[0]
    if return_type != contract["normalReturnType"]:
        raise ValueError(f"native-normal-return={return_type}")
    pack_parameter = next(item for item in parameters
                          if image.metadata.string(item.name_index) == "damagePackData")
    byref = bool(_runtime_type(image, pack_parameter.type_index)[1][11] & 0x20)
    if byref is not contract["damagePackDataByref"]:
        raise ValueError(f"native-damage-pack-byref={byref}")

    checked_fields = []
    for owner_name, field_name, expected_type, expected_offset, expected_token in contract["fields"]:
        owners = [item for item in image.metadata.types
                  if image.metadata.type_full_name(item) == owner_name]
        if len(owners) != 1:
            raise ValueError(f"native-field-owner={owner_name}:{len(owners)}")
        owner = owners[0]
        fields = [item for item in image.metadata.fields_for(owner)
                  if image.metadata.string(item.name_index) == field_name]
        if len(fields) != 1:
            raise ValueError(f"native-field-count={owner_name}.{field_name}:{len(fields)}")
        field = fields[0]
        type_name = _runtime_type(image, field.type_index)[0]
        offsets = il2cpp.runtime_type_field_offsets(
            image.metadata, image.pe, image.registration, owner.index,
        )
        offset = offsets.get(field_name)
        if (type_name != expected_type or offset != expected_offset
                or f"0x{field.token:08x}" != expected_token):
            raise ValueError(
                f"native-field={owner_name}.{field_name}:type={type_name}:offset={offset}"
            )
        checked_fields.append({"owner": owner_name, "name": field_name,
                               "type": type_name, "offset": offset})
    attacker_attributes = checked_fields[-1]
    if (attacker_attributes["owner"] != "Beyond.Gameplay.Core.DamagePackData"
            or attacker_attributes["name"] != "attackerAttributes"
            or attacker_attributes["offset"] - 16
            != contract["damagePackDataUnboxedAttackerAttributesOffset"]):
        raise ValueError("native-damage-pack-unboxed-offset")

    windows = contract["codeWindows"]
    if len(windows) != 4:
        raise ValueError("contract-code-window-count")
    image.check_windows([
        {**row, "startRva": _rva(row["startRva"]), "endRva": _rva(row["endRva"])}
        for row in windows
    ], label="damage-route")
    calls = contract["callTargets"]
    if len(calls) != 6:
        raise ValueError("contract-call-count")
    for site_text, role in calls:
        site = _rva(site_text)
        raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
        if raw[:1] != b"\xe8":
            raise ValueError(f"native-call-opcode={site:#x}")
        target = site + 5 + struct.unpack_from("<i", raw, 1)[0]
        expected = _rva(role) if role.startswith("0x") else resolved[role]
        if target != expected:
            raise ValueError(f"native-call-target={site:#x}:actual={target:#x}")
    return {"method": methods["normal"], "normalParameters": actual,
            "fields": checked_fields, "codeWindows": [
                {key: row[key] for key in ("startRva", "endRva", "sha256")}
                for row in windows], "callSites": len(calls)}


def audit(*, gameassembly: Path, metadata: Path,
          contract_path: Path = CONTRACT) -> dict[str, Any]:
    contract, digest = read_reviewed_contract(
        contract_path, schema=SCHEMA, status="validated", label="damage-route",
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
        report.update(_validate(NativeImage(gameassembly, metadata, label="damage-route"), contract))
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
