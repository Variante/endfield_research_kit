"""Validate the selected native BreakingAttackCalculation.Evaluate proof.

The reviewed contract binds stored fields, attribute operands, mixed-precision
arithmetic and the iFix bypass to one explicit installed IL2CPP pair.

On the normally returning unpatched path, attacker ``AttributeType.Atk (2)``
(``A``) and defender ``BreakingAttackDamageTakenScalar (27)`` (``D``) reach
``CalculationBase.GetAttribute`` with their override arrays, and the stored
``multiplier`` (``M``) and ``atkScale`` (``S``) ``BlackboardDouble`` fields
reach ``GetValue``. The attributes return ``Double`` and the scales
``Single``; the body multiplies the attributes in ``Double``, the scales in
``Single``, narrows the attribute product to ``Single``, multiplies the two
``Single`` values and widens the result: ``Double(Single(S * M) * Single(D *
A))``. The server debug-args path rejoins that arithmetic; the patched iFix
path returns a wrapper result instead and carries no formula claim.

Pass the explicit ``--gameassembly``/``--metadata`` pair; the default report
is ``reports/game_data/breaking_attack_calculation_native.json``.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.game_data.il2cpp.reviewed_program import validate as validate_reviewed_program
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "breaking_attack_calculation_native.json"
SCHEMA = "endfield.breaking-attack-calculation-native-contract.v2"
REPORT_SCHEMA = "endfield.breaking-attack-calculation-native-audit.v2"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/breaking_attack_calculation_native.json"


def _validate_body(image: NativeImage, contract: dict[str, Any]) -> dict[str, Any]:
    return validate_reviewed_program(image, contract, label="breaking_attack_native")


def audit(*, gameassembly: Path, metadata: Path, contract_path: Path = CONTRACT) -> dict[str, Any]:
    contract, digest = read_reviewed_contract(
        contract_path, schema=SCHEMA, label="breaking-attack", status="validated",
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
    image = NativeImage(gameassembly, metadata, label="breaking-attack")
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
