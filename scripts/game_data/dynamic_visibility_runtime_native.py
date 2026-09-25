"""Reprove named DynamicStreaming visibility controller paths offline.

The reviewed claims carry no build pin. The caller selects both installed
IL2CPP inputs and their expected hashes; the evaluator records current native
body identities and fails closed if any named field or call claim moves.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex, evaluate
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import field_defaults, native_enum_members
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_visibility_runtime_claims.json"
SCHEMA = "endfield.dynamic-visibility-runtime-claims.v16"
FORMAT = "endfield.dynamic-visibility-runtime-claims-audit.v3"
DEFAULT_OUTPUT = REPO_ROOT / "reports/animestudio/dynamic_visibility_runtime_claims_latest.json"
DEFAULT_FAILURE_OUTPUT = REPO_ROOT / "reports/animestudio/dynamic_visibility_runtime_claims_failure_latest.json"


class DynamicVisibilityRuntimeError(ValueError):
    """Selected inputs or reviewed claim contract cannot be evaluated."""


def audit(
    *, gameassembly: Path, metadata: Path,
    expected_gameassembly_sha256: str, expected_metadata_sha256: str,
) -> dict[str, Any]:
    contract, digest = read_reviewed_contract(
        CONTRACT, schema=SCHEMA, label="dynamic_visibility_runtime", status="validated",
    )
    methods = contract.get("methods")
    if not isinstance(methods, dict) or not methods:
        raise DynamicVisibilityRuntimeError("dynamic_visibility_runtime.contract:methods missing")
    enum_claims = contract.get("enumClaims")
    if not isinstance(enum_claims, dict) or not enum_claims:
        raise DynamicVisibilityRuntimeError("dynamic_visibility_runtime.contract:enumClaims missing")
    for name, expected in enum_claims.items():
        if not isinstance(name, str) or not isinstance(expected, dict) or not expected or any(
            not isinstance(member, str) or type(value) is not int
            for member, value in expected.items()
        ):
            raise DynamicVisibilityRuntimeError(
                f"dynamic_visibility_runtime.contract:invalid enum claim {name!r}"
            )
    gate = check_installed_native_inputs(
        expected_gameassembly_sha256, expected_metadata_sha256,
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicVisibilityRuntimeError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    image = open_native_image(gameassembly, metadata)
    rows, failures = evaluate(BodyIndex(image), methods)
    if len(rows) + len({failure["symbol"] for failure in failures if failure["claim"] == "resolve"}) != len(methods):
        raise DynamicVisibilityRuntimeError("dynamic_visibility_runtime:method row cardinality differs")
    defaults = field_defaults(image.metadata)
    enums = []
    for type_name, expected in enum_claims.items():
        try:
            members = native_enum_members(
                image.metadata, defaults, image.pe, image.registration, type_name,
            )
        except (RuntimeError, ValueError, KeyError, IndexError) as exc:
            failures.append({
                "symbol": type_name, "claim": "enumMembers", "reason": str(exc),
            })
            continue
        actual = {member["name"]: member["id"] for member in members}
        enums.append({"type": type_name, "members": members})
        if actual != expected:
            failures.append({
                "symbol": type_name,
                "claim": "enumMembers",
                "reason": f"expected={expected!r} actual={actual!r}",
            })
    return {
        "format": FORMAT,
        "status": "pendingReview" if failures else "validated",
        "contractSha256": digest,
        "nativeInputs": {
            "gameAssemblySha256": gate.gameassembly_sha256.upper(),
            "metadataSha256": gate.metadata_sha256.upper(),
        },
        "methods": rows,
        "enums": enums,
        "failures": failures,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--expected-gameassembly-sha256", required=True)
    parser.add_argument("--expected-metadata-sha256", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--failure-output", type=Path, default=DEFAULT_FAILURE_OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = audit(
            gameassembly=args.gameassembly, metadata=args.metadata,
            expected_gameassembly_sha256=args.expected_gameassembly_sha256,
            expected_metadata_sha256=args.expected_metadata_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as exc:
        print(f"dynamic-visibility-runtime-native: {exc}", file=sys.stderr)
        return 1
    if report["status"] != "validated":
        args.failure_output.parent.mkdir(parents=True, exist_ok=True)
        args.failure_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for failure in report["failures"][:8]:
            print(
                "dynamic-visibility-runtime-native: "
                f"{failure['symbol']}: {failure['reason']}", file=sys.stderr,
            )
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"DynamicStreaming visibility runtime claims passed: methods={len(report['methods'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
