#!/usr/bin/env python3
"""Verify the pinned native secondary-dynamics callback/writeback contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_callback_contract as builder  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> int:
    if not builder.DEFAULT_OUTPUT.is_file():
        fail(f"missing callback contract: {builder.DEFAULT_OUTPUT}")
    expected = json.loads(builder.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    observed = builder.build_contract()
    if observed != expected:
        fail(
            "installed/source evidence no longer matches the reviewed callback contract; "
            "run build_secondary_dynamics_callback_contract.py and review the diff"
        )
    if expected.get("status") != "native_callback_writeback_closed":
        fail(f"unexpected contract status: {expected.get('status')!r}")
    if expected.get("secondary_dynamics_verified") is not False:
        fail("secondary_dynamics_verified must remain false until visual verification")
    callbacks = expected.get("callbacks") or []
    if len(callbacks) != 7:
        fail("seven callback wrappers are not pinned")
    selectors = expected.get("simulationSelectors") or {}
    if selectors.get("fixedUpdateRunsClothUpdate") is not False:
        fail("FixedUpdate must not be classified as a ClothUpdate callback")
    if selectors.get("mutuallyExclusiveWholePipeline") is not True:
        fail("PreLate callbacks are not classified as mutually exclusive whole-pipeline selectors")
    writeback = expected.get("writeback") or {}
    stages = writeback.get("stages") or {}
    if stages.get("transformWriteback") != [3004, 4277]:
        fail("transform writeback offsets drifted")
    print(json.dumps({"status": expected["status"], "callbacks": len(callbacks), "writebackOffsets": stages["transformWriteback"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
