"""Reprove the named SetAudioCueVar.Execute body calls on a selected client.

The claims establish call sites and their order. They do not establish which
runtime branch executes, the values written, or an AudioCueTable selection.

This is a build-independent claims validator. Its contract,
`contracts/levelscript_audio_cue_execute_claims.json`, names the method by
type and method rather than pinning an address, and `il2cpp.body_claims`
re-proves it on whichever build `--game-root` (the installed `Endfield_Data`
directory, required) selects. The claims state that the body reads all seven
authored `Param` fields and contains ordered call sites for an iFix state
check, the typed string, float, int and bool GameAction cue-variable setters,
and an iFix patch lookup. The audit is written to
`reports/game_data/levelscript_audio_cue_execute_latest.json` (`--output`);
the command exits nonzero unless every claim holds. The stored
`SetAudioCueVar` route itself is checked by `levelscript_audio_cue_native`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex, evaluate
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.levelscript-audio-cue-execute-claims.v1"
LABEL = "levelscriptAudioCueExecuteNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_audio_cue_execute_claims.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/levelscript_audio_cue_execute_latest.json"


def audit_audio_cue_execute(
    *, game_root: Path, contract_path: Path = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    """Return a fail-closed audit for an explicitly selected installed pair."""
    try:
        contract, digest = read_reviewed_contract(
            Path(contract_path), schema=SCHEMA, label=LABEL, status="reviewed",
        )
        methods = contract.get("methods")
        if (
            contract.get("evidenceBoundary") != "conditional"
            or not isinstance(methods, dict) or not methods
            or any(
                not isinstance(spec, dict)
                or not isinstance(spec.get("type"), str)
                or not isinstance(spec.get("method"), str)
                or not isinstance(spec.get("claims"), list)
                or not spec["claims"]
                for spec in methods.values()
            )
        ):
            raise ValueError(f"{LABEL}.contract:shape")
        root = Path(game_root)
        gate = check_installed_native_inputs(
            gameassembly=root.parent / "GameAssembly.dll",
            metadata=root / "il2cpp_data/Metadata/global-metadata.dat",
        )
        base = {
            "schema": "endfield.levelscript-audio-cue-execute-audit.v1",
            "validator": LABEL,
            "contractSha256": digest,
            "evidenceBoundary": "conditional",
            "nativeInputs": {
                "gameAssemblySha256": gate.gameassembly_sha256.upper(),
                "metadataSha256": gate.metadata_sha256.upper(),
            },
        }
        if gate.status != "validated":
            return {**base, "status": gate.status, "failedCheck": "installed-native-inputs",
                    "detail": gate.detail, "methods": [], "failures": []}
        image = open_native_image(gate.gameassembly, gate.metadata)
        rows, failures = evaluate(BodyIndex(image), methods)
        if len(rows) + sum(failure.get("claim") == "resolve" for failure in failures) != len(methods):
            raise ValueError(f"{LABEL}.native:method-cardinality")
        return {
            **base, "status": "pendingReview" if failures else "validated",
            "failedCheck": "body-claims" if failures else None,
            "detail": f"{len(failures)} claim failure(s)" if failures else "",
            "methods": rows, "failures": failures,
        }
    except (OSError, ValueError, KeyError, IndexError, TypeError, RuntimeError) as exc:
        return {
            "schema": "endfield.levelscript-audio-cue-execute-audit.v1",
            "validator": LABEL, "status": "validation_failed",
            "failedCheck": "contract-or-native-evaluation", "detail": str(exc)[:500],
            "methods": [], "failures": [{"gate": "contract-or-native-evaluation", "actual": str(exc)[:500]}],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True,
                        help="installed Endfield_Data directory")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = audit_audio_cue_execute(game_root=args.game_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{LABEL}: {result['status']} methods={len(result['methods'])} "
          f"failures={len(result['failures'])}")
    if result["status"] != "validated":
        print(f"  {result.get('failedCheck')}: {result.get('detail')}", file=sys.stderr)
        for failure in result["failures"][:5]:
            print(f"  {failure.get('symbol', failure.get('gate'))}: {failure.get('reason', failure.get('actual'))}",
                  file=sys.stderr)
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
