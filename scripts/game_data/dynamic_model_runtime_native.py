"""Reprove DynamicStreaming model-placement and collider-activation claims.

Named body claims survive address changes without carrying a build pin. The
caller explicitly selects native inputs and expected hashes. A failed gate
returns no methods; a changed claim is pending review, never a live-use fact.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.il2cpp.body_claims import BodyIndex, evaluate
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT

CONTRACT = CONTRACTS_DIR/"dynamic_model_runtime_claims.json"
SCHEMA = "endfield.dynamic-model-runtime-claims.v1"


def audit(*, gameassembly: Path, metadata: Path, expected_gameassembly_sha256: str,
          expected_metadata_sha256: str) -> dict:
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="dynamic-model-runtime")
    gate = check_installed_native_inputs(expected_gameassembly_sha256, expected_metadata_sha256,
                                         gameassembly=gameassembly, metadata=metadata)
    report = dict(schema=SCHEMA, status=gate.status, methods=[], failures=[], contractSha256=digest,
                  nativeInputs=dict(gameAssemblySha256=gate.gameassembly_sha256,
                                    metadataSha256=gate.metadata_sha256),
                  evidenceBoundary=contract["evidenceBoundary"])
    if gate.status != "validated":
        report["failures"] = [dict(check="installed_native_inputs", detail=gate.detail)]
        return report
    methods = {}
    for group in contract["groups"].values():
        for symbol, method in group["methods"].items():
            if symbol in methods:
                raise ValueError(f"duplicate reviewed dynamic-model symbol: {symbol}")
            methods[symbol] = method
    rows, failures = evaluate(BodyIndex(open_native_image(gameassembly, metadata)), methods)
    if not failures and ({row["symbol"] for row in rows} != set(methods) or len(rows) != len(methods)):
        failures.append(dict(check="method_coverage", expected=len(methods), actual=len(rows),
                             detail="evaluated method identities differ from the reviewed claims"))
    report.update(status="pendingReview" if failures else "validated", methods=rows, failures=failures)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--expected-gameassembly-sha256", required=True)
    parser.add_argument("--expected-metadata-sha256", required=True)
    parser.add_argument("--output", type=Path, default=REPO_ROOT/"reports/animestudio/dynamic_model_runtime_claims_latest.json")
    parser.add_argument("--failure-output", type=Path, default=REPO_ROOT/"reports/animestudio/dynamic_model_runtime_claims_failure_latest.json")
    args = parser.parse_args(argv)
    try:
        report = audit(gameassembly=args.gameassembly, metadata=args.metadata,
                       expected_gameassembly_sha256=args.expected_gameassembly_sha256,
                       expected_metadata_sha256=args.expected_metadata_sha256)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        report = dict(schema=SCHEMA, status="pendingReview", methods=[],
                      failures=[dict(check="native_claims", detail=str(error)[:1200])])
    destination = args.output if report["status"] == "validated" else args.failure_output
    atomic_write_text(destination, json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(dict(status=report["status"], methods=len(report["methods"]),
                         failures=report["failures"][:4], report=str(destination)), ensure_ascii=False), flush=True)
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
