"""Authenticate one selected native field read for a common ExtendData task.

This is a static consumer check. It does not join a decoded graph record to a
runtime instance or infer the behavior tag's meaning.
"""

from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run as: python -m scripts.game_data.extend_data_tasks_native")

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets


CONTRACT = CONTRACTS_DIR / "extend_data_tasks_native.json"
SCHEMA = "endfield.extend-data-tasks-native-contract.v1"
AUDIT_SCHEMA = "endfield.extend-data-tasks-native-audit.v1"


def _check_native(image: Any, contract: dict[str, Any]) -> dict[str, Any]:
    task = contract["taskType"]
    if image.type_name(task["index"]) != task["name"]:
        raise ValueError("task type differs")
    fields = runtime_type_field_offsets(image.metadata, image.pe, image.registration, task["index"])
    if fields.get(task["field"]) != task["fieldOffset"]:
        raise ValueError("task field offset differs")
    image.validate_method_row(contract["method"], label="extend-data-tasks-native")
    image.check_windows(contract["codeWindows"], label="extend-data-tasks-native")
    image.check_instruction_windows(contract["instructionWindows"], label="extend-data-tasks-native")
    return {
        "taskType": task["name"],
        "field": task["field"],
        "fieldOffset": task["fieldOffset"],
        "method": contract["method"][2],
        "codeWindowCount": len(contract["codeWindows"]),
        "instructionWindowCount": len(contract["instructionWindows"]),
        "semanticLimits": contract["semanticLimits"],
    }


def audit_extend_data_tasks_native(
    *, contract_path: Path = CONTRACT, gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    contract, contract_sha = read_reviewed_contract(
        contract_path, schema=SCHEMA, label="extend-data-tasks-native", status="validated"
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
        report["fieldRead"] = _check_native(image, contract)
    except (ValueError, RuntimeError, KeyError, IndexError) as error:
        report.update(status="mismatched", detail=f"native proof failed: {error}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = audit_extend_data_tasks_native(
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
