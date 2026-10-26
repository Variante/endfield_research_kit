"""Audit the selected DamageAction route from a stored Poise calculation.

The result proves a conditional intermediate PoisePackData input. It does not
observe action execution or calculate an applied or displayed Poise amount.

``DamageAction._ProcessDamage`` indexes ``DamageActionData.damageUnits``,
saves that ``DamageUnit`` and tests its ``poiseCalculation`` for null. On the
normally returning unpatched branch with a nonnull field it constructs
``PoisePackData``, calls ``ApplyPoiseModifier(BeforeCalculation)``, passes the
stored calculation pointer to the calculation-object helper, and copies the
returned ``CalcResult.value`` into the unboxed ``PoisePackData.calcResult.value``
slot when the post-evaluator guard allows continuation. This route does not use
the ``simpleCalculation`` attack selector. It does not prove which virtual
subtype ran or what the blackboard resolved. Where a row stores
``DefiniteValueCalculation`` and dispatch selects it, that evaluator's own
contract gives the conditional input (``GetDoubleValue(value)``, times
``Double(GetValue(valueScale))`` when ``applyScale``); the value entering
``PoisePackData`` is not a final Poise amount. The per-row partition of stored
Poise subtypes lives in the generated ``character_damage_routes.json`` report.

Pass the explicit ``--gameassembly``/``--metadata`` pair; the default report
is ``reports/game_data/damage_action_poise_route_native.json``.
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


CONTRACT = CONTRACTS_DIR / "damage_action_poise_route_native.json"
SCHEMA = "endfield.damage-action-poise-route-native-contract.v2"
REPORT_SCHEMA = "endfield.damage-action-poise-route-native-audit.v2"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/damage_action_poise_route_native.json"


def _validate(image: NativeImage, contract: dict[str, Any]) -> dict[str, Any]:
    return validate_reviewed_program(image, contract, label="damage_action_poise_route_native")


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
