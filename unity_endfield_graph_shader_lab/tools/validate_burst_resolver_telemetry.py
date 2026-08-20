"""Fail-closed validator for Burst resolver telemetry JSONL captures."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import burst_resolver_telemetry as telemetry  # noqa: E402


SCHEMA = telemetry.EVENT_SCHEMA


class TraceValidationError(ValueError):
    pass


def _fail(message: str) -> None:
    raise TraceValidationError(message)


def load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        _fail(f"trace not found: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                _fail(f"{path}:{line_number}: invalid JSON: {exc.msg}")
            if not isinstance(value, dict):
                _fail(f"{path}:{line_number}: row is not an object")
            rows.append(value)
    if not rows:
        _fail("trace contains no rows")
    return rows


def _verified_files(start: dict[str, Any], manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    facts = start.get("verifiedFiles")
    if not isinstance(facts, dict) or set(facts) != set(manifest["files"]):
        _fail("session_start verifiedFiles must contain exactly the three pinned native files")
    for name, expected in manifest["files"].items():
        actual = facts.get(name)
        if not isinstance(actual, dict):
            _fail(f"session_start missing verified file fact {name}")
        if actual.get("bytes") != expected["bytes"]:
            _fail(f"session_start verified file fact drift for {name} bytes")
        if str(actual.get("sha256", "")).casefold() != expected["sha256"].casefold():
            _fail(f"session_start verified file fact drift for {name} sha256")
        if not isinstance(actual.get("path"), str) or not actual["path"]:
            _fail(f"session_start verified file fact {name} has no path")
    return facts


def _check_pointer(value: Any, label: str, *, allow_null: bool = False) -> None:
    if allow_null and value is None:
        return
    if not isinstance(value, str) or not value:
        _fail(f"{label} must be a non-empty pointer string")
    if not value.lower().startswith("0x"):
        _fail(f"{label} is not a pointer string")
    if not allow_null and value.lower() in {"0x0", "0x0000000000000000"}:
        _fail(f"{label} must not be null")


def _module_name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{label} must be a non-empty module name")
    return value.casefold()


def validate_trace(
    path: Path,
    manifest_path: Path = telemetry.DEFAULT_MANIFEST,
) -> dict[str, Any]:
    manifest = telemetry.load_manifest(manifest_path.resolve())
    rows = load_rows(path.resolve())
    session_values = [row.get("sessionId") for row in rows]
    if any(not isinstance(value, str) or not value for value in session_values):
        _fail("trace rows must have a non-empty string sessionId")
    if len(set(session_values)) != 1:
        _fail("trace must contain exactly one non-empty sessionId")
    expected_seq = 0
    for index, row in enumerate(rows):
        if row.get("schema") != SCHEMA:
            _fail(f"row {index} has unexpected schema {row.get('schema')!r}")
        if row.get("seq") != expected_seq:
            _fail(f"row {index} sequence is {row.get('seq')!r}, expected {expected_seq}")
        expected_seq += 1
        if not isinstance(row.get("kind"), str) or not row["kind"]:
            _fail(f"row {index} has no event kind")

    starts = [row for row in rows if row.get("kind") == "session_start"]
    ends = [row for row in rows if row.get("kind") == "session_end"]
    handshakes = [row for row in rows if row.get("kind") == "native_module_verified"]
    if len(starts) != 1 or len(ends) != 1 or len(handshakes) != 1:
        _fail(
            "expected exactly one session_start/native_module_verified/session_end, got "
            f"{len(starts)}/{len(handshakes)}/{len(ends)}"
        )
    start = starts[0]
    if start.get("gameBuild") != manifest["gameBuild"]:
        _fail("session gameBuild differs from the pinned manifest")
    if start.get("exportFingerprint") != manifest["files"]["metadata"]["sha256"]:
        _fail("session metadata fingerprint differs from the pinned manifest")
    if _module_name(start.get("kernel32ModuleName"), "session kernel32ModuleName") != manifest["kernel32ModuleName"].casefold():
        _fail("session kernel32 module differs from the pinned manifest")
    if _module_name(start.get("resolverModuleName"), "session resolverModuleName") != manifest["resolverModuleName"].casefold():
        _fail("session resolver module differs from the pinned manifest")
    file_facts = _verified_files(start, manifest)

    handshake = handshakes[0]
    for key in ("modulePathMatch", "moduleSizeMatch"):
        if handshake.get(key) is not True:
            _fail(f"native module handshake did not validate {key}")
    if handshake.get("verifiedFiles") != file_facts:
        _fail("native module handshake file facts differ from session_start")
    if _module_name(handshake.get("kernel32ModuleName"), "handshake kernel32ModuleName") != manifest["kernel32ModuleName"].casefold():
        _fail("native module handshake kernel32 name drifted")
    if _module_name(handshake.get("resolverModuleName"), "handshake resolverModuleName") != manifest["resolverModuleName"].casefold():
        _fail("native module handshake resolver module name drifted")
    hook_states = handshake.get("hookStates")
    if not isinstance(hook_states, dict) or set(hook_states) != set(manifest["hooks"]):
        _fail("native module handshake does not list both resolver hooks")
    if any(value != "attached" for value in hook_states.values()):
        _fail("native module handshake does not prove every resolver hook attached")
    resolver_identity = handshake.get("resolverModuleIdentity")
    if not isinstance(resolver_identity, dict):
        _fail("native module handshake has no resolver module identity")
    if _module_name(resolver_identity.get("name"), "resolver module identity name") != manifest["resolverModuleName"].casefold():
        _fail("resolver module identity name drifted")
    identity_handle = resolver_identity.get("base")
    if identity_handle is not None:
        _check_pointer(identity_handle, "resolver module identity base")

    resolver_events = [row for row in rows if row.get("kind") == "resolver_module_loaded"]
    proc_events = [row for row in rows if row.get("kind") == "get_proc_address"]
    observed_handles: set[str] = set()
    if isinstance(identity_handle, str) and identity_handle:
        observed_handles.add(identity_handle.casefold())
    for index, row in enumerate(resolver_events):
        requested = row.get("requestedPath")
        if not isinstance(requested, str) or not requested:
            _fail(f"resolver_module_loaded {index} has no requestedPath")
        if requested.replace("/", "\\").casefold().split("\\")[-1] != manifest["resolverModuleName"].casefold():
            _fail(f"resolver_module_loaded {index} requested a different module")
        _check_pointer(row.get("hModule"), f"resolver_module_loaded {index} hModule")
        if row.get("loadSucceeded") is True:
            observed_handles.add(str(row["hModule"]).casefold())
            module = row.get("module")
            if not isinstance(module, dict) or _module_name(module.get("name"), f"resolver_module_loaded {index} module name") != manifest["resolverModuleName"].casefold():
                _fail(f"resolver_module_loaded {index} has no matching module identity")
        elif row.get("loadSucceeded") is not False:
            _fail(f"resolver_module_loaded {index} loadSucceeded is invalid")

    for index, row in enumerate(proc_events):
        handle = row.get("hModule")
        _check_pointer(handle, f"get_proc_address {index} hModule")
        if str(handle).casefold() not in observed_handles:
            _fail(f"get_proc_address {index} does not match the observed resolver HMODULE")
        name = row.get("lpProcName")
        if name is not None and not isinstance(name, str):
            _fail(f"get_proc_address {index} lpProcName is not a string or null")
        if row.get("lpProcNameType") not in {"name", "ordinal", "null", "unreadable"}:
            _fail(f"get_proc_address {index} lpProcNameType is invalid")
        _check_pointer(row.get("returnPointer"), f"get_proc_address {index} returnPointer")
        backtrace = row.get("gameAssemblyCallerBacktrace")
        if not isinstance(backtrace, list) or len(backtrace) > manifest["capture"]["maxBacktraceFrames"]:
            _fail(f"get_proc_address {index} GameAssembly backtrace exceeds its bound")
        for frame_index, frame in enumerate(backtrace):
            if not isinstance(frame, dict):
                _fail(f"get_proc_address {index} backtrace frame {frame_index} is not an object")
            if _module_name(frame.get("module"), f"get_proc_address {index} backtrace module") != manifest["moduleName"].casefold():
                _fail(f"get_proc_address {index} backtrace contains a non-GameAssembly frame")
            _check_pointer(frame.get("address"), f"get_proc_address {index} backtrace address")
            _check_pointer(frame.get("offset"), f"get_proc_address {index} backtrace offset", allow_null=True)
        if row.get("backtraceStatus") not in {"gameassembly_frames", "no_gameassembly_frame", "unavailable"}:
            _fail(f"get_proc_address {index} backtraceStatus is invalid")

    terminal_kinds = {
        "capture_fatal",
        "capture_capped",
        "capture_detached",
        "capture_stop_ack_missing",
        "capture_not_started",
        "capture_start_rejected",
    }
    terminal_rows = [row for row in rows if row.get("kind") in terminal_kinds]
    if terminal_rows:
        _fail(f"trace contains terminal failure state: {terminal_rows[0]}")
    started_rows = [row for row in rows if row.get("kind") == "capture_started"]
    stop_acks = [row for row in rows if row.get("kind") == "capture_stop_ack"]
    if len(started_rows) != 1:
        _fail(f"expected exactly one capture_started row, got {len(started_rows)}")
    if len(stop_acks) != 1:
        _fail(f"expected exactly one capture_stop_ack row, got {len(stop_acks)}")
    if ends[0].get("stopAck") is not True or ends[0].get("terminalFailure") is not False:
        _fail("session_end does not confirm a clean stop acknowledgement")
    if len(resolver_events) + len(proc_events) > manifest["capture"]["maxEvents"]:
        _fail("trace exceeds configured event cap")

    return {
        "schema": "burstResolverTelemetry.validation.v1",
        "status": "observed_runtime_candidate",
        "trace": str(path.resolve()),
        "sessionId": next(iter(set(session_values))),
        "gameBuild": manifest["gameBuild"],
        "resolverModuleName": manifest["resolverModuleName"],
        "resolverModuleIdentity": resolver_identity,
        "rowCount": len(rows),
        "resolverModuleEventCount": len(resolver_events),
        "getProcAddressEventCount": len(proc_events),
        "nativeModuleVerified": True,
        "claims": {
            "readOnlyHookEvents": True,
            "resolverModuleIdentityObserved": bool(observed_handles),
            "getProcAddressResolutionObserved": bool(proc_events),
            "gameAssemblyCallerBacktraceObserved": any(
                row.get("backtraceStatus") == "gameassembly_frames" and row.get("gameAssemblyCallerBacktrace")
                for row in proc_events
            ),
            "resolverExportMappingProven": False,
            "gameStateWritten": False,
        },
        "evidenceBoundary": manifest["evidenceBoundary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--manifest", type=Path, default=telemetry.DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = validate_trace(args.trace, args.manifest)
    except (OSError, ValueError, telemetry.CaptureConfigurationError) as exc:
        print(f"Burst resolver telemetry validation failed: {exc}", file=sys.stderr)
        return 1
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "resolverModuleEventCount": result["resolverModuleEventCount"],
                "getProcAddressEventCount": result["getProcAddressEventCount"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
