"""Audit the selected BlowOffAction source fields and runtime call boundary."""
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


CONTRACT = CONTRACTS_DIR / "buff_1b_action_native.json"
SCHEMA = "endfield.buff-1b-action-native-contract.v1"
REPORT_SCHEMA = "endfield.buff-1b-action-native-audit.v1"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/buff_1b_action_native.json"
WRAPPER = "Beyond.MemoryPack.Beyond_Gameplay_Core_BlowOffAction_DataForMemoryPack"


def _rva(value: str) -> int:
    if not isinstance(value, str) or re.fullmatch(r"0x[0-9a-f]+", value) is None:
        raise ValueError(f"contract-rva={value!r}")
    return int(value, 16)


def _runtime_type(image: NativeImage, type_index: int) -> str:
    registration = image.registration
    if not 0 <= type_index < int(registration["typesCount"]):
        raise ValueError(f"native-type-index={type_index}")
    pointer = image.pe.u64_at_va(int(registration["types"], 16) + type_index * 8)
    if pointer == 0:
        raise ValueError(f"native-type-pointer={type_index}")
    return il2cpp.runtime_type_name(image.pe, image.metadata, pointer)


def _direct_call(image: NativeImage, site: int, target: int) -> None:
    raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if len(raw) != 5 or raw[0] != 0xE8:
        raise ValueError(f"blowoff.native:call-opcode={site:#x}")
    actual = site + 5 + struct.unpack_from("<i", raw, 1)[0]
    if actual != target:
        raise ValueError(f"blowoff.native:call-target={site:#x}:actual={actual:#x}")


def validate(image: NativeImage, contract: dict[str, Any]) -> dict[str, Any]:
    methods = contract["methods"]
    if set(methods) != {"reader", "execute", "applyBlowOff"}:
        raise ValueError("blowoff.contract:method-set")
    resolved: dict[str, int] = {}
    for role, row in methods.items():
        if len(row) != 4:
            raise ValueError(f"blowoff.contract:method-row={role}")
        image.validate_method_row([*row[:3], _rva(row[3])], label="blowoff")
        resolved[role] = _rva(row[3])
    if methods["reader"][1] != WRAPPER:
        raise ValueError("blowoff.contract:reader-owner")

    data_index, data_name = contract["dataType"]
    if image.type_name(data_index) != data_name:
        raise ValueError("blowoff.native:data-type")
    owner = image.metadata.types[data_index]
    fields = {image.metadata.string(row.name_index): row
              for row in image.metadata.fields_for(owner)}
    offsets = il2cpp.runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, data_index,
    )
    source_fields = contract["serializedFields"]
    if len(source_fields) != 13 or len({row[0] for row in source_fields}) != 13:
        raise ValueError("blowoff.contract:field-count")
    if {row[0] for row in source_fields} != set(fields):
        raise ValueError("blowoff.native:field-set")
    call_sites = []
    for name, type_name, offset, token, setter_index, setter_rva, call_rva in source_fields:
        field = fields[name]
        if (_runtime_type(image, field.type_index) != type_name
                or offsets.get(name) != offset
                or f"0x{field.token:08x}" != token):
            raise ValueError(f"blowoff.native:field={name}")
        setter_name = f"set___{name}__"
        image.validate_method_row(
            [setter_index, WRAPPER, setter_name, _rva(setter_rva)], label="blowoff",
        )
        setter = image.metadata.methods[setter_index]
        parameters = image.metadata.parameters_for(setter)
        if len(parameters) != 1 or _runtime_type(image, parameters[0].type_index) != type_name:
            raise ValueError(f"blowoff.native:setter-type={name}")
        call_site = _rva(call_rva)
        if not resolved["reader"] <= call_site < _rva(contract["codeWindows"][0]["endRva"]):
            raise ValueError(f"blowoff.contract:setter-site={name}")
        _direct_call(image, call_site, _rva(setter_rva))
        call_sites.append(call_site)
    if call_sites != sorted(call_sites) or len(set(call_sites)) != len(call_sites):
        raise ValueError("blowoff.contract:setter-order")

    apply = image.metadata.methods[methods["applyBlowOff"][0]]
    actual_parameters = [
        [image.metadata.string(row.name_index), _runtime_type(image, row.type_index)]
        for row in image.metadata.parameters_for(apply)
    ]
    if actual_parameters != contract["applyBlowOffParameters"]:
        raise ValueError(f"blowoff.native:apply-parameters={actual_parameters!r}")
    windows = [
        {**row, "startRva": _rva(row["startRva"]), "endRva": _rva(row["endRva"])}
        for row in contract["codeWindows"]
    ]
    if len(windows) != 2 or windows[0]["startRva"] != resolved["reader"] or windows[1]["startRva"] != resolved["execute"]:
        raise ValueError("blowoff.contract:windows")
    image.check_windows(windows, label="blowoff")
    for site_text, role in contract["directCalls"]:
        if role not in resolved:
            raise ValueError(f"blowoff.contract:call-role={role}")
        site = _rva(site_text)
        if not windows[1]["startRva"] <= site < windows[1]["endRva"]:
            raise ValueError(f"blowoff.contract:runtime-call-site={site_text}")
        _direct_call(image, site, resolved[role])
    return {
        "dataType": data_name,
        "sourceFieldOrder": [row[0] for row in source_fields],
        "applyBlowOffParameters": actual_parameters,
        "directCalls": contract["directCalls"],
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def audit(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    contract, digest = read_reviewed_contract(
        CONTRACT, schema=SCHEMA, label="blowoff", status="validated",
    )
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["gameAssemblySha256"], expected["metadataSha256"],
        gameassembly=gameassembly, metadata=metadata,
    )
    report = {
        "schema": REPORT_SCHEMA,
        "contractPath": str(CONTRACT),
        "contractSha256": digest,
        "nativeInputs": {
            "status": gate.status,
            "detail": gate.detail,
            "gameAssemblySha256": gate.gameassembly_sha256,
            "metadataSha256": gate.metadata_sha256,
        },
    }
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return {**report, "status": gate.status}
    image = NativeImage(gate.gameassembly, gate.metadata, label="blowoff")
    return {**report, "status": "validated", "result": validate(image, contract)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = audit(gameassembly=args.gameassembly, metadata=args.metadata)
    if report["status"] != "validated":
        print(f"[buff-1b-action] skipped: {report['nativeInputs']['detail']}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[buff-1b-action] validated 13 source fields and ApplyBlowOff call; {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
