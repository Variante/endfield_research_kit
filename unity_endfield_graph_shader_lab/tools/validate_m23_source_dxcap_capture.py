#!/usr/bin/env python3
"""Validate the foreground M23 source-renderer DXCap baseline.

This is deliberately a negative retail-shader boundary: the maintained source
player preserves ParticleSystemRenderer identity but assigns the local
VFXBaseV2SampleStack diagnostic material.  A passing report therefore requires
the known stride-60, 3036/3956 draw and rejects any exact 136-byte candidate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA = "endfield.lizhiyan-m23-source-dxcap-baseline.v1"
RUNTIME_SCHEMA = "endfield.lizhiyan-m23-particle-renderer-capture.v1"
DXCAP_SCHEMA = "endfield.dxcap-d3d11-evidence.v2"


def validate(runtime: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, expected: Any, actual: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), "expected": expected, "actual": actual})

    check("runtime.schema", runtime.get("schema") == RUNTIME_SCHEMA, RUNTIME_SCHEMA, runtime.get("schema"))
    for key, expected in (
        ("status", "pass"), ("graphicsDeviceType", "Direct3D11"),
        ("applicationIsBatchMode", False), ("sourceRendererSubmissionPath", True),
        ("noBakeMeshContract", True), ("noProxyContract", True),
        ("exactIdentityClosed", True), ("foregroundWindowRequested", True),
        ("foregroundWindowHandleNonZero", True), ("foregroundWindowIsWindow", True),
    ):
        check(f"runtime.{key}", runtime.get(key) == expected, expected, runtime.get(key))
    check("runtime.particleCount", isinstance(runtime.get("particleCount"), int) and runtime["particleCount"] > 0, ">0", runtime.get("particleCount"))
    check("dxcap.schema", evidence.get("schema") == DXCAP_SCHEMA, DXCAP_SCHEMA, evidence.get("schema"))

    draws = evidence.get("draw_calls") if isinstance(evidence.get("draw_calls"), list) else []
    source_draws = []
    exact_candidates = []
    bounded = []
    for draw in draws:
        candidate = draw.get("m23_candidate") if isinstance(draw.get("m23_candidate"), dict) else {}
        lengths = (candidate.get("vs_bytecode_length"), candidate.get("ps_bytecode_length"))
        strides = sorted({row.get("stride") for row in draw.get("ia_vertex_buffers", []) if isinstance(row.get("stride"), int)})
        index_count = draw.get("parameters", {}).get("index_count")
        if lengths == (3036, 3956) and 60 in strides and index_count in (1728, 3456):
            source_draws.append(draw)
        if candidate.get("exact_m23_candidate") is True:
            exact_candidates.append(draw)
        bounded.append({"moment": draw.get("moment"), "drawType": draw.get("draw_type"), "indexCount": index_count, "vsBytes": lengths[0], "psBytes": lengths[1], "strides": strides})
    check("dxcap.source_draw_unique", len(source_draws) == 1, 1, len(source_draws))
    check("dxcap.exact_candidate_absent", not exact_candidates, 0, len(exact_candidates))
    failures = [row for row in checks if not row["passed"]]
    return {
        "schema": SCHEMA,
        "status": "pass" if not failures else "fail",
        "checks": checks,
        "summary": {"checks": len(checks), "failures": len(failures), "firstFailure": failures[0]["name"] if failures else None},
        "draws": bounded,
        "claimBoundary": "proves foreground stock ParticleSystemRenderer submission with the local diagnostic shader; does not prove a retail VFXBaseV2 variant, 136-byte packing, VB bytes, cb3 bytes, or visual fidelity",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime", type=Path)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    try:
        report = validate(json.loads(args.runtime.read_text(encoding="utf-8")), json.loads(args.evidence.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report = {"schema": SCHEMA, "status": "fail", "summary": {"firstFailure": "input.read"}, "error": str(exc)}
    payload = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    else:
        print(payload, end="")
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
