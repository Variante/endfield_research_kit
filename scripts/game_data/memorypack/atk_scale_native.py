"""Validate the selected native AtkScaleCalculation.Evaluate proof.

The reviewed contract binds its signature, operands and arithmetic to exact
selected-build bytes. The claim covers normally returning nonpatch paths, not
an observed DamageUnit invocation or final damage.

The signature names ``attacker`` and an optional ``attackerOverrideAttributes:
double[]``. With a nonnull array longer than two, the body reads element 2,
the selected ``AttributeType.Atk`` index; with a null array it calls
``attacker.get_atk()``; a present shorter array takes a failure path instead
of falling back. The stored ``atkScale: BlackboardDouble`` reaches
``ActionBlackboardExtensions.GetValue`` with the action blackboard; its
``Single`` result is converted to ``Double`` and multiplied by the selected
attack into ``CalcResult.value``. The optional server debug-args path rejoins
the same multiplication. The proved intermediate is ``attack *
resolved(atkScale)`` -- present in character skills, but not a final damage
number.

Pass the explicit ``--gameassembly``/``--metadata`` pair; the default report
is ``reports/game_data/atk_scale_calculation_native.json``.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.game_data.il2cpp.reviewed_program import validate as validate_reviewed_program
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "atk_scale_calculation_native.json"
SCHEMA = "endfield.atk-scale-calculation-native-contract.v2"
REPORT_SCHEMA = "endfield.atk-scale-calculation-native-audit.v2"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/atk_scale_calculation_native.json"


def _validate_body(image: NativeImage, contract: dict[str, Any]) -> dict[str, Any]:
    return validate_reviewed_program(image, contract, label="atk_scale_native")


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
