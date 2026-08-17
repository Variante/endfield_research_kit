#!/usr/bin/env python3
"""Validate the safe, external-only M23 draw-correlation boundary.

This validator joins a stock DXCap ``-toXML`` evidence summary to the
external telemetry harness manifest.  It intentionally stops at a candidate
draw: DXCap call state can identify shader bytecode *lengths* and IA stride,
but external telemetry cannot identify a managed/native HG renderer object or
read its constant-buffer/vertex-buffer bytes.  Those gaps are represented in
the output instead of being filled by inference.

The validator never opens a process handle, reads process memory, enumerates
modules, or accepts an injected/runtime-hook attestation.  Its only inputs are
already-exported JSON files.  It is therefore useful even when the retail
client blocks a profiler: a passing result says exactly what the capture
proves and what it cannot prove.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "endfield.m23-external-correlation.v1"
DXCAP_SCHEMA = "endfield.dxcap-d3d11-evidence.v2"
LAB_ROOT = Path(__file__).resolve().parents[1]

_FORBIDDEN_ATTESTATION_FLAGS = (
    "clientAttachedByHarness",
    "debuggerAttached",
    "codeInjected",
    "clientOrDriverPatched",
    "processMemoryRead",
    "processModulesEnumerated",
    "commandLineCollected",
    "registryWritten",
    "vulkanLayersAltered",
    "serviceOrDriverStateChanged",
    "protectionDisabledOrEvaded",
    "credentialsOrTokensCollected",
    "networkTrafficCaptured",
    "keyboardOrMouseInputTracked",
    "stockGraphicsProfilerUsed",
)


def _check(name: str, passed: bool, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "expected": expected,
        "actual": actual,
    }


def _load(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read JSON {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def _validate_manifest(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    checks.append(_check("telemetry.schema_version", manifest.get("schemaVersion") == 1,
                         1, manifest.get("schemaVersion")))
    policy = manifest.get("policy")
    boundary = policy.get("configurationBoundary") if isinstance(policy, Mapping) else None
    checks.append(_check("telemetry.external_only_boundary",
                         boundary == "external_telemetry_only",
                         "external_telemetry_only", boundary))
    intrusive = policy.get("intrusiveCaptureAttempted") if isinstance(policy, Mapping) else None
    checks.append(_check("telemetry.intrusive_capture_not_attempted",
                         intrusive is False, False, intrusive))
    attestation = manifest.get("harnessActionAttestation")
    if not isinstance(attestation, Mapping):
        checks.append(_check("telemetry.attestation.present", False, True, None))
    else:
        checks.append(_check("telemetry.attestation.present", True, True, True))
        for field in _FORBIDDEN_ATTESTATION_FLAGS:
            actual = bool(attestation.get(field, False))
            checks.append(_check(f"telemetry.attestation.{field}", not actual, False, actual))

    capabilities = manifest.get("capabilities")
    accepted = capabilities.get("acceptedClientProcessCount") if isinstance(capabilities, Mapping) else None
    checks.append(_check("telemetry.accepted_client_process_count", accepted == 1, 1, accepted))
    pins = capabilities.get("configuredBinaryPinsMatch") if isinstance(capabilities, Mapping) else None
    checks.append(_check("telemetry.configured_binary_pins_match", pins is True, True, pins))
    return checks


def validate_documents(
    dxcap: Mapping[str, Any],
    telemetry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a bounded report; never promote a candidate to exact parity."""

    checks: list[dict[str, Any]] = []
    checks.append(_check("dxcap.schema", dxcap.get("schema") == DXCAP_SCHEMA, DXCAP_SCHEMA, dxcap.get("schema")))
    draws = dxcap.get("draw_calls")
    if not isinstance(draws, list):
        draws = []
    candidates = [
        draw for draw in draws
        if isinstance(draw, Mapping)
        and isinstance(draw.get("m23_candidate"), Mapping)
        and draw["m23_candidate"].get("exact_m23_candidate") is True
    ]
    checks.append(_check("dxcap.candidate_draw_present", bool(candidates), True, len(candidates)))

    if telemetry is None:
        checks.append(_check("telemetry.manifest_present", False, True, False))
    else:
        checks.extend(_validate_manifest(telemetry))

    failed = [check for check in checks if check["status"] == "fail"]
    # Even a fully-attested external run cannot identify the HG object.  The
    # only safe correlation is a draw candidate within the captured process/
    # frame; exact shader bytes and cb3/VB payloads remain unavailable.
    return {
        "schema": SCHEMA,
        "status": "pass" if not failed else "fail",
        "summary": {
            "checks": len(checks),
            "failed": len(failed),
            "firstFailure": failed[0]["name"] if failed else None,
            "candidateDrawCount": len(candidates),
        },
        "checks": checks,
        "correlation": {
            "drawCandidate": bool(candidates) and not failed,
            "shaderPair": "length_candidate_only",
            "iaStride": "observed_136_candidate" if candidates else "unavailable",
            "actorObjectIdentity": "unavailable_external_only",
            "actorIdentityClaimAllowed": False,
            "vertexBufferBytes": "unavailable_external_only",
            "vsCb3Bytes": "unavailable_external_only",
            "correlationKind": "process_and_capture_frame_only",
        },
        "admission": {
            "externalTelemetryOnly": not failed,
            "exactShaderByteParity": False,
            "exactPackedRowParity": False,
            "drawTimeCb3Available": False,
            "actorIdentityClosed": False,
            "visualAdmission": False,
        },
        "candidateDraws": [
            {
                "moment": draw.get("moment"),
                "drawType": draw.get("draw_type"),
                "parameters": draw.get("parameters", {}),
                "vertexBuffers": draw.get("ia_vertex_buffers", []),
                "vsHandle": draw.get("vs_handle"),
                "psHandle": draw.get("ps_handle"),
            }
            for draw in candidates
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dxcap-evidence", type=Path, required=True)
    parser.add_argument("--telemetry-manifest", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)
    try:
        dxcap = _load(args.dxcap_evidence)
        telemetry = _load(args.telemetry_manifest) if args.telemetry_manifest else None
        report = validate_documents(dxcap, telemetry)
    except ValueError as exc:
        print(json.dumps({"schema": SCHEMA, "status": "parse_failed", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    else:
        print(payload, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
