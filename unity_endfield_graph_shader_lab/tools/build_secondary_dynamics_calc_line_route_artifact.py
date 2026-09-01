#!/usr/bin/env python3
"""Build and verify an immutable, fail-closed CalcLine runtime route artifact.

The general Burst telemetry validator deliberately publishes
``observed_runtime_candidate``.  This tool promotes only the one CalcLine
decision needed by the inert Unity selector, and only when the candidate has
one complete, mutually exclusive route closure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


TOOLS = Path(__file__).resolve().parent
REPO_ROOT = TOOLS.parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import burst_resolver_telemetry as telemetry  # noqa: E402
import validate_burst_resolver_telemetry as trace_validator  # noqa: E402


SCHEMA = "endfield.charinfo.secondary-dynamics-calc-line-route.v1"
STATUS = "validated_runtime_route"
SOURCE_VALIDATION_SCHEMA = "burstResolverTelemetry.validation.v3"
SOURCE_VALIDATION_STATUS = "observed_runtime_candidate"
TOP_LEVEL_KEYS = {
    "schema", "status", "artifactSha256", "source", "nativeIdentity",
    "route", "selectorObservation", "evidenceBoundary",
}


class RouteArtifactError(ValueError):
    """Raised when live evidence does not close exactly one CalcLine route."""


def _fail(message: str) -> None:
    raise RouteArtifactError(message)


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_json(value: str) -> None:
    _fail(f"non-finite JSON number {value!r} is not permitted")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        _fail(f"{label} not found: {path}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_object,
            parse_constant=_reject_nonfinite_json,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail(f"unable to read {label} {path}: {exc}")
    if not isinstance(value, dict):
        _fail(f"{label} root is not an object")
    return value


def _load_trace_rows_strict(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(
                        line,
                        object_pairs_hook=_json_object,
                        parse_constant=_reject_nonfinite_json,
                    )
                except json.JSONDecodeError as exc:
                    _fail(f"trace {path}:{line_number} is invalid JSON: {exc.msg}")
                if not isinstance(value, dict):
                    _fail(f"trace {path}:{line_number} row is not an object")
                seq = value.get("seq")
                if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
                    _fail(f"trace {path}:{line_number} seq is not a non-negative integer")
                monotonic_ms = value.get("monotonicMs")
                if (
                    isinstance(monotonic_ms, bool)
                    or not isinstance(monotonic_ms, (int, float))
                    or not math.isfinite(monotonic_ms)
                    or monotonic_ms < 0
                ):
                    _fail(f"trace {path}:{line_number} monotonicMs is not finite and non-negative")
                rows.append(value)
    except (OSError, UnicodeDecodeError) as exc:
        _fail(f"unable to read trace {path}: {exc}")
    if not rows:
        _fail(f"trace {path} contains no rows")
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_fact(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "path": str(resolved),
        "bytes": resolved.stat().st_size,
        "sha256": _sha256(resolved),
    }


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _canonical_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        _fail(f"{label} schema is not exact: expected {sorted(expected)}, got {actual}")
    return value


def _load_source(
    validation_path: Path,
    manifest_path: Path,
) -> tuple[
    dict[str, Any], dict[str, Any], list[dict[str, Any]], Path,
    dict[str, dict[str, Any]],
]:
    validation_path = validation_path.resolve()
    manifest_path = manifest_path.resolve()
    validation_fact = _file_fact(validation_path)
    manifest_fact = _file_fact(manifest_path)
    supplied = _load_json(validation_path, "validation report")
    if supplied.get("schema") != SOURCE_VALIDATION_SCHEMA:
        _fail(f"validation report schema must be {SOURCE_VALIDATION_SCHEMA!r}")
    if supplied.get("status") != SOURCE_VALIDATION_STATUS:
        _fail(
            "validation report must remain an observed_runtime_candidate input; "
            "only this builder may publish the closed route"
        )
    trace_value = supplied.get("trace")
    if not isinstance(trace_value, str) or not trace_value:
        _fail("validation report has no trace path")
    trace_path = Path(trace_value).resolve()
    trace_fact = _file_fact(trace_path)
    try:
        regenerated = trace_validator.validate_trace(trace_path, manifest_path)
    except (OSError, ValueError, telemetry.CaptureConfigurationError) as exc:
        _fail(f"referenced trace did not independently revalidate: {exc}")
    # Python considers ``True == 1`` and ``False == 0``.  Plain container
    # equality would therefore let malformed JSON types pass this source
    # closure even though the independently regenerated report is different.
    if _canonical_json(supplied) != _canonical_json(regenerated):
        _fail("validation report differs from independent trace validation")
    # The general validator predates this promotion boundary and uses the
    # standard JSON decoder.  Read the source once more with duplicate-key and
    # non-finite-number rejection so ambiguous JSONL cannot become a route.
    rows = _load_trace_rows_strict(trace_path)
    manifest = telemetry.load_manifest(manifest_path)
    source_facts = {
        "validation": validation_fact,
        "trace": trace_fact,
        "manifest": manifest_fact,
    }
    for label, path in (
        ("validation", validation_path),
        ("trace", trace_path),
        ("manifest", manifest_path),
    ):
        if _canonical_json(_file_fact(path)) != _canonical_json(source_facts[label]):
            _fail(f"{label} source changed while route evidence was being read")
    return supplied, manifest, rows, trace_path, source_facts


def _native_identity(
    validation: dict[str, Any], manifest: dict[str, Any], rows: list[dict[str, Any]],
) -> dict[str, Any]:
    handshakes = [row for row in rows if row.get("kind") == "native_module_verified"]
    starts = [row for row in rows if row.get("kind") == "session_start"]
    if len(handshakes) != 1 or len(starts) != 1:
        _fail("trace must contain exactly one native identity handshake")
    handshake = handshakes[0]
    start = starts[0]
    verified = start.get("verifiedFiles")
    if not isinstance(verified, dict):
        _fail("session_start has no verified native file identities")

    gameassembly = manifest["files"]["gameAssembly"]
    resolver = manifest["files"]["resolver"]
    for name, expected in (("gameAssembly", gameassembly), ("resolver", resolver)):
        actual = verified.get(name)
        if not isinstance(actual, dict):
            _fail(f"session_start has no pinned {name} file identity")
        if actual.get("bytes") != expected["bytes"] or actual.get("sha256") != expected["sha256"]:
            _fail(f"session_start {name} identity differs from the pinned manifest")

    runtime_resolver = validation.get("resolverModuleIdentity")
    if not isinstance(runtime_resolver, dict):
        _fail("closed route has no runtime resolver handshake identity")
    if runtime_resolver.get("status") == "not_loaded_at_attach":
        if any(runtime_resolver.get(key) is not None for key in ("path", "base", "moduleBase", "size")):
            _fail("not-loaded resolver handshake contains a partial runtime identity")
    else:
        if runtime_resolver.get("size") != resolver["bytes"]:
            _fail("runtime resolver size differs from the pinned resolver")
        if not isinstance(runtime_resolver.get("base"), str):
            _fail("loaded runtime resolver has no module base")

    return {
        "gameBuild": manifest["gameBuild"],
        "gameAssemblyDisk": {
            "name": manifest["moduleName"],
            "relativePath": gameassembly["relativePath"],
            "bytes": gameassembly["bytes"],
            "sha256": gameassembly["sha256"],
        },
        "gameAssemblyRuntime": {
            "path": handshake["attachedModulePath"],
            "base": handshake["gameAssemblyModuleBase"],
            "bytes": handshake["gameAssemblyModuleSize"],
        },
        "resolverDisk": {
            "name": manifest["resolverModuleName"],
            "relativePath": resolver["relativePath"],
            "bytes": resolver["bytes"],
            "sha256": resolver["sha256"],
        },
        # A clean prelaunch capture can legitimately attach before the
        # resolver exists.  The Burst route's later loaded base/path/size are
        # then carried by route.cpuSelectionObservation; the immutable disk
        # identity remains pinned here in either branch.
        "resolverRuntimeHandshake": runtime_resolver,
        "resolverExportMap": {
            "count": manifest["resolverExportEnumeration"]["hashedCount"],
            "canonicalNameRvaSha256": manifest["resolverExportEnumeration"]["canonicalNameRvaSha256"],
        },
    }


def _route(
    validation: dict[str, Any], manifest: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    burst_events = validation.get("calcLineBurstGateObservations")
    if not isinstance(burst_events, list) or len(burst_events) != 1:
        _fail("route closure requires exactly one CalcLine Burst gate observation")
    burst_event = burst_events[0]
    burst_enabled = burst_event.get("result")
    if not isinstance(burst_enabled, bool):
        _fail("CalcLine Burst gate result is not boolean")

    selection = _exact_keys(
        validation.get("calcLineCpuSelection"),
        {
            "targetId", "functionPointerSlotRva", "observationCount", "status",
            "directCallTargetObserved", "selectedCpuVariant", "selectedCpuEntryRva",
        },
        "calcLineCpuSelection",
    )
    probe = manifest["calcLineCpuSelection"]
    if selection["targetId"] != probe["targetId"] or selection["functionPointerSlotRva"] != probe["functionPointerSlotRva"]:
        _fail("CalcLine CPU selection identity differs from the pinned manifest")
    ifix_events = validation.get("calcLineIfixGateObservations")
    if not isinstance(ifix_events, list):
        _fail("CalcLine IFix gate observations are not a list")

    mappings = validation.get("burstFunctionPointerMappings")
    if not isinstance(mappings, dict):
        _fail("validation report has no Burst function-pointer mappings")
    calc_mappings = mappings.get(probe["targetId"])
    if not isinstance(calc_mappings, list):
        _fail("validation report has no CalcLine function-pointer mapping list")
    matched = [
        row for row in calc_mappings
        if isinstance(row, dict)
        and isinstance(row.get("cpuSelection"), dict)
        and row["cpuSelection"].get("status") == "matched"
    ]

    if burst_enabled:
        if ifix_events:
            _fail("cross-route conflict: Burst and IFix route evidence are both present")
        if len(matched) != 1 or len(calc_mappings) != 1:
            _fail("Burst route requires exactly one matched CalcLine CPU selection")
        cpu = matched[0]["cpuSelection"]
        variant = selection.get("selectedCpuVariant")
        variants = {row["cpuVariant"]: row["entryRva"] for row in probe["variants"]}
        if (
            selection.get("observationCount") != 1
            or selection.get("status") != "selected_cpu_variant_observed"
            or selection.get("directCallTargetObserved") is not True
            or variant not in variants
            or selection.get("selectedCpuEntryRva") != variants[variant]
            or cpu.get("selectedCpuVariant") != variant
            or cpu.get("resolvedModuleOffset") != variants[variant]
        ):
            _fail("matched CalcLine CPU selection is incomplete or internally inconsistent")
        execution_route = "BurstX64Sse2" if variant == "x64_sse2" else "BurstAvx2"
        selector = {
            "traceValidated": True,
            "burstGateObservationCount": 1,
            "burstEnabled": True,
            "directCallTargetObserved": True,
            "cpuSelectionObservationCount": 1,
            "cpuVariant": variant,
            "ifixGateObservationCount": 0,
            "ifixPatched": False,
            "ifixCalcLineRoute": None,
        }
        route = {
            "kind": "burst_cpu_variant",
            "executionRoute": execution_route,
            "targetId": probe["targetId"],
            "burstGateObservation": burst_event,
            "cpuSelectionObservation": cpu,
            "ifixGateObservation": None,
        }
        return route, selector

    if matched or calc_mappings or selection.get("observationCount") != 0 or selection.get("status") != "missing":
        _fail("cross-route conflict: disabled Burst gate carries CPU-route evidence")
    if selection.get("directCallTargetObserved") is not False or selection.get("selectedCpuVariant") is not None or selection.get("selectedCpuEntryRva") is not None:
        _fail("disabled Burst route carries a selected CPU target")
    if len(ifix_events) != 1:
        _fail("managed route requires exactly one IFix direct-call fallback observation")
    ifix = ifix_events[0]
    if ifix.get("calcLineRoute") != "direct_call_fallback" or ifix.get("result") is not False:
        _fail("managed route requires one explicitly unpatched direct_call_fallback IFix observation")
    selector = {
        "traceValidated": True,
        "burstGateObservationCount": 1,
        "burstEnabled": False,
        "directCallTargetObserved": False,
        "cpuSelectionObservationCount": 0,
        "cpuVariant": None,
        "ifixGateObservationCount": 1,
        "ifixPatched": False,
        "ifixCalcLineRoute": "direct_call_fallback",
    }
    route = {
        "kind": "managed_unpatched_direct_call_fallback",
        "executionRoute": "ManagedUnpatched",
        "targetId": probe["targetId"],
        "burstGateObservation": burst_event,
        "cpuSelectionObservation": None,
        "ifixGateObservation": ifix,
    }
    return route, selector


def build_artifact(
    validation_path: Path,
    manifest_path: Path = telemetry.DEFAULT_MANIFEST,
) -> dict[str, Any]:
    validation, manifest, rows, trace_path, source_facts = _load_source(
        validation_path, manifest_path,
    )
    if validation.get("nativeModuleVerified") is not True:
        _fail("validation report does not prove the native module handshake")
    claims = validation.get("claims")
    if not isinstance(claims, dict) or claims.get("gameStateWritten") is not False:
        _fail("validation report does not preserve the read-only evidence boundary")
    route, selector = _route(validation, manifest)
    payload = {
        "schema": SCHEMA,
        "status": STATUS,
        "source": {
            "validation": {
                **source_facts["validation"],
                "schema": validation["schema"],
                "status": validation["status"],
            },
            "trace": {
                **source_facts["trace"],
                "schema": telemetry.EVENT_SCHEMA,
                "sessionId": validation["sessionId"],
            },
            "manifest": {
                **source_facts["manifest"],
                "schema": manifest["schema"],
            },
        },
        "nativeIdentity": _native_identity(validation, manifest, rows),
        "route": route,
        "selectorObservation": selector,
        "evidenceBoundary": {
            "classification": "validated_runtime_route",
            "consumer": "EndfieldSecondaryDynamicsCalcLineRouteSelection.TrySelect",
            "solverConnected": False,
            "transformWritebackConnected": False,
            "nonClaim": "The artifact selects an inert value-kernel route only; it does not prove later indirect-call completion or authorize scene/solver/writeback integration.",
        },
    }
    return {**payload, "artifactSha256": _canonical_digest(payload)}


def validate_artifact(
    artifact_path: Path,
    validation_path: Path | None = None,
    manifest_path: Path = telemetry.DEFAULT_MANIFEST,
) -> dict[str, Any]:
    artifact = _exact_keys(_load_json(artifact_path.resolve(), "route artifact"), TOP_LEVEL_KEYS, "route artifact")
    digest = artifact.get("artifactSha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        _fail("route artifact has no canonical SHA-256")
    unsigned = {key: value for key, value in artifact.items() if key != "artifactSha256"}
    if _canonical_digest(unsigned) != digest:
        _fail("route artifact canonical SHA-256 differs from its content")
    if artifact.get("schema") != SCHEMA or artifact.get("status") != STATUS:
        _fail("route artifact is not a closed validated runtime route")
    source_validation = artifact.get("source", {}).get("validation", {})
    recorded_path = source_validation.get("path")
    if not isinstance(recorded_path, str) or not recorded_path:
        _fail("route artifact has no validation source path")
    selected_validation = (validation_path or Path(recorded_path)).resolve()
    if str(selected_validation) != str(Path(recorded_path).resolve()):
        _fail("supplied validation path differs from the immutable source path")
    expected = build_artifact(selected_validation, manifest_path)
    # Preserve JSON type identity as well as values.  In particular, reject a
    # recomputed artifact whose integer observation count was changed to a
    # boolean that Python's normal dict equality would otherwise accept.
    if _canonical_json(artifact) != _canonical_json(expected):
        _fail("route artifact differs from the independently rebuilt contract")
    return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("validation", type=Path, help="validator v3 JSON report")
    parser.add_argument("--manifest", type=Path, default=telemetry.DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true", help="verify an existing artifact without writing")
    args = parser.parse_args(argv)
    try:
        if args.check:
            validate_artifact(args.output, args.validation, args.manifest)
            print(f"checked closed CalcLine route artifact {args.output.resolve()}")
            return 0
        artifact = build_artifact(args.validation, args.manifest)
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        validate_artifact(output, args.validation, args.manifest)
        print(f"wrote closed CalcLine route artifact {output}")
        return 0
    except (OSError, RouteArtifactError, telemetry.CaptureConfigurationError) as exc:
        print(f"CalcLine route artifact failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
