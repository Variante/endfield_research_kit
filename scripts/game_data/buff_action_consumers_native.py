"""Re-prove narrow Buff action consumer calls on the explicitly selected build.

This is a native consumer audit, independent of MemoryPack coverage. A group
whose named claims no longer hold becomes pendingReview and supplies no rows.
Compiled call presence never proves live branch selection or value ownership.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex, evaluate
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract

CONTRACT_PATH = CONTRACTS_DIR / "buff_action_consumers_native.json"
SCHEMA = "endfield.buff-action-consumer-claims.v1"


def load_consumer_claims(*, gameassembly: Path | None = None,
                        metadata: Path | None = None) -> dict[str, Any]:
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA,
        status="reviewed", label="buff_action_consumers")
    gate = check_installed_native_inputs(gameassembly=gameassembly, metadata=metadata)
    result = {"schema": "endfield.buff-action-consumer-audit.v1",
              "status": gate.status, "detail": gate.detail,
              "contract": CONTRACT_PATH.as_posix(), "groups": {}, "failures": [],
              "evidenceBoundary": contract["evidenceBoundary"], "runtimeMeaningExact": False}
    if gate.status != "validated":
        return result
    pins = {"GameAssembly.dll": gate.gameassembly_sha256,
            "global-metadata.dat": gate.metadata_sha256}
    result["nativeInputs"] = pins
    index = BodyIndex(open_native_image(gate.gameassembly, gate.metadata))
    for name, group in contract["groups"].items():
        rows, failures = evaluate(index, group["methods"])
        diagnostics = [{**f, "group": name, "validator": "buff_action_consumers",
                        "source": CONTRACT_PATH.as_posix(), "nativeInputs": pins}
                       for f in failures]
        result["failures"].extend(diagnostics)
        result["groups"][name] = {"status": "pendingReview" if failures else "validated",
                                   "rows": [] if failures else rows,
                                   "failures": diagnostics}
    after = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != "validated":
        result.update(status=after.status, detail=after.detail, groups={})
        result["failures"].append({"validator": "buff_action_consumers",
            "check": "native-inputs-after", "source": str(gate.gameassembly),
            "expected": pins, "actual": after.detail})
        return result
    result["status"] = "pendingReview" if result["failures"] else "validated"
    result["detail"] = f"{len(result['failures'])} failed claim(s)" if result["failures"] else ""
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    # Every tool artifact belongs under an ignored root.
    from scripts.repo_paths import REPO_ROOT
    target = args.output.resolve()
    if not any(target.is_relative_to(REPO_ROOT / root) for root in ("reports", "scratch", "tmp")):
        parser.error("--output must be under reports/, scratch/ or tmp/")
    result = load_consumer_claims(gameassembly=args.gameassembly, metadata=args.metadata)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "groups": {k: v["status"] for k, v in result["groups"].items()},
                      "failures": result["failures"], "detail": result["detail"]}, ensure_ascii=False))
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
