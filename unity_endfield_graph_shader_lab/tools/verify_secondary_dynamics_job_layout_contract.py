#!/usr/bin/env python3
"""Fail-closed verifier for the generated secondary-dynamics job layout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_job_layout_contract as builder


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=builder.DEFAULT_OUTPUT)
    parser.add_argument("--game-assembly", type=Path, default=builder.DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=builder.DEFAULT_METADATA)
    args = parser.parse_args()
    try:
        expected = builder.build_contract(
            game_assembly=args.game_assembly,
            metadata=args.metadata,
        )
        if not args.contract.is_file():
            raise builder.ContractError(f"missing contract: {args.contract}")
        actual = json.loads(args.contract.read_text(encoding="utf-8"))
        if actual != expected:
            raise builder.ContractError(
                "contract differs from a fresh MetadataRegistration/GameAssembly reconstruction"
            )
        if actual.get("status") != "outer_job_layout_closed":
            raise builder.ContractError("contract is not closed at the outer-job boundary")
        if not actual.get("outer_job_layout_recovered") or actual.get("job_payload_layout_recovered"):
            raise builder.ContractError("outer/full layout status flags are inconsistent")
        print(json.dumps({"status": "validated", "contract": str(args.contract)}))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, builder.ContractError) as exc:
        print(json.dumps({"status": "unavailable", "validationFailures": [str(exc)]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
