"""Validate a captured character-dynamics telemetry JSONL stream.

Validation keeps the observation boundary explicit: it can confirm the
hash-pinned module handshake, bounded opaque events, and the selected target
label, but it never promotes a pointer to an actor, bone, or solver result.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import character_dynamics_telemetry as telemetry  # noqa: E402


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


def validate_trace(path: Path, manifest_path: Path = telemetry.DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest = telemetry.load_manifest(manifest_path.resolve())
    rows = load_rows(path.resolve())
    session_ids = {row.get("sessionId") for row in rows}
    if len(session_ids) != 1 or not next(iter(session_ids or {None})):
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
    if len(starts) != 1 or len(ends) != 1:
        _fail(f"expected exactly one session_start/session_end, got {len(starts)}/{len(ends)}")
    start = starts[0]
    target_id = start.get("targetId")
    if not isinstance(target_id, str) or target_id not in manifest["targets"]:
        _fail(f"session targetId is not a manifest target: {target_id!r}")
    target = manifest["targets"][target_id]
    if start.get("target") != target:
        _fail("session target metadata differs from the pinned manifest")
    if start.get("gameBuild") != manifest["gameBuild"]:
        _fail("session gameBuild differs from the pinned manifest")
    if start.get("exportFingerprint") != manifest["files"]["metadata"]["sha256"]:
        _fail("session metadata fingerprint differs from the pinned manifest")
    handshakes = [row for row in rows if row.get("kind") == "native_module_verified"]
    if len(handshakes) != 1:
        _fail(f"expected exactly one native_module_verified row, got {len(handshakes)}")
    handshake = handshakes[0]
    for key in ("modulePathMatch", "moduleSizeMatch"):
        if handshake.get(key) is not True:
            _fail(f"native module handshake did not validate {key}")
    known_hooks = set(manifest["hooks"])
    hook_events = [row for row in rows if row.get("kind") in {"hook_enter", "hook_leave"}]
    hook_counts: dict[str, int] = {name: 0 for name in known_hooks}
    for index, row in enumerate(hook_events):
        hook = row.get("hook")
        if hook not in known_hooks:
            _fail(f"hook event {index} references unknown hook {hook!r}")
        hook_counts[hook] += 1
        if row.get("kind") == "hook_enter":
            registers = row.get("registers")
            if not isinstance(registers, dict):
                _fail(f"hook_enter {index} has no register object")
            snapshots = [
                value.get("snapshot")
                for value in registers.values()
                if isinstance(value, dict) and isinstance(value.get("snapshot"), dict)
            ]
            if len(snapshots) > manifest["capture"]["maxPointerReadsPerEvent"]:
                _fail(f"hook_enter {index} exceeds pointer snapshot bound")
            for snapshot in snapshots:
                status = snapshot.get("status")
                if status == "read":
                    if snapshot.get("length") != manifest["capture"]["readBytesPerPointer"]:
                        _fail(f"hook_enter {index} snapshot length drift")
                    if not isinstance(snapshot.get("bytes"), str) or len(snapshot["bytes"]) != snapshot["length"] * 2:
                        _fail(f"hook_enter {index} snapshot bytes are malformed")
                elif status not in {"null", "unreadable"}:
                    _fail(f"hook_enter {index} has unknown snapshot status {status!r}")
    fatal = [row for row in rows if row.get("kind") == "agent_fatal"]
    if fatal:
        _fail(f"trace contains agent_fatal: {fatal[0]}")
    native_events = len(hook_events)
    if native_events > manifest["capture"]["maxEvents"]:
        _fail("trace exceeds configured native event cap")
    return {
        "schema": "characterDynamicsTelemetry.validation.v1",
        "status": "observed_runtime_candidate",
        "trace": str(path.resolve()),
        "sessionId": next(iter(session_ids)),
        "gameBuild": manifest["gameBuild"],
        "targetId": target_id,
        "actorLabel": target["actor"],
        "identityStatus": target.get("identityStatus", "unresolved"),
        "rowCount": len(rows),
        "nativeEventCount": native_events,
        "hookEventCounts": hook_counts,
        "nativeModuleVerified": True,
        "claims": {
            "readOnlyHookEvents": True,
            "transformOutputObserved": hook_counts.get("transformWriteback", 0) > 0,
            "actorIdentityProven": target.get("identityStatus") == "exact",
            "solverImplemented": False,
            "retailEquivalent": False,
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
        print(f"Character dynamics telemetry validation failed: {exc}", file=sys.stderr)
        return 1
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.output.resolve().write_text(serialized, encoding="utf-8", newline="\n")
    print(json.dumps({"status": result["status"], "targetId": result["targetId"], "nativeEventCount": result["nativeEventCount"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
