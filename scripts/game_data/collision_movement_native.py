"""Reprove available character movement/query routes on selected native inputs.

This checks named body claims, not live query results or contact delivery.
Build drift is evaluated afresh; no address or contract digest is a gate.
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

CONTRACT = CONTRACTS_DIR / "collision_movement_queries.json"
SCHEMA = "endfield.collision-movement-query-claims.v1"


def audit(*, gameassembly: Path, metadata: Path,
          expected_gameassembly_sha256: str, expected_metadata_sha256: str) -> dict:
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA,
                                             label="collision-movement", status="reviewed")
    gate = check_installed_native_inputs(expected_gameassembly_sha256, expected_metadata_sha256,
                                         gameassembly=gameassembly, metadata=metadata)
    report = dict(schema=SCHEMA, status=gate.status, methods=[], failures=[],
                  contractSha256=digest, evidenceBoundary=contract["evidenceBoundary"],
                  nativeInputs=dict(gameAssemblyPath=str(gameassembly), metadataPath=str(metadata),
                                    gameAssemblySha256=gate.gameassembly_sha256,
                                    metadataSha256=gate.metadata_sha256))
    if gate.status != "validated":
        report["failures"] = [dict(check="installed_native_inputs", detail=gate.detail)]
        return report
    methods = contract["methods"]
    if not methods or not all(spec.get("claims") for spec in methods.values()):
        raise ValueError("collision-movement: reviewed methods must have claims")
    rows, failures = evaluate(BodyIndex(open_native_image(gameassembly, metadata)), methods)
    if not failures and (len(rows) != len(methods) or {row["symbol"] for row in rows} != set(methods)):
        failures.append(dict(check="method_coverage", expected=len(methods), actual=len(rows),
                             detail="evaluated identities differ from reviewed methods"))
    report.update(status="pendingReview" if failures else "validated", failures=failures,
                  methods=[] if failures else rows)
    return report


def output_path(path: Path) -> Path:
    resolved = path.resolve()
    if not any(resolved.is_relative_to(REPO_ROOT/name) for name in ("reports", "scratch", "tmp")):
        raise ValueError("collision-movement: generated output must be under reports/, scratch/ or tmp/")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--expected-gameassembly-sha256", required=True)
    parser.add_argument("--expected-metadata-sha256", required=True)
    parser.add_argument("--output", type=Path, default=REPO_ROOT/"reports/runtime_capture/collision/movement-query-claims.json")
    parser.add_argument("--failure-output", type=Path, default=REPO_ROOT/"reports/runtime_capture/collision/movement-query-claims-failure.json")
    args = parser.parse_args(argv)
    success_path, failure_path = output_path(args.output), output_path(args.failure_output)
    try:
        report = audit(gameassembly=args.gameassembly, metadata=args.metadata,
                       expected_gameassembly_sha256=args.expected_gameassembly_sha256,
                       expected_metadata_sha256=args.expected_metadata_sha256)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        report = dict(schema=SCHEMA, status="pendingReview", methods=[],
                      failures=[dict(check="collision_movement_native", detail=str(error)[:1200])])
    destination = success_path if report["status"] == "validated" else failure_path
    atomic_write_text(destination, json.dumps(report, indent=2)+"\n")
    print(json.dumps(dict(status=report["status"], methods=len(report["methods"]),
                         failures=report["failures"][:4], report=str(destination))), flush=True)
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
