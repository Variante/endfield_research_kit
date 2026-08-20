"""Capture bounded read-only secondary-dynamics telemetry from the retail client.

This is an opt-in external observation tool for the pinned client build.  It
does not implement the cloth solver and it does not identify a character from
an opaque native pointer.  The user labels a capture target and opens that
actor's Character Info overview while the trace is armed.

Examples (from the repository root)::

    python unity_endfield_graph_shader_lab/tools/character_dynamics_telemetry.py \
        --target chen-overview --check-only
    tools\\frida-runtime\\venv\\Scripts\\python.exe \
        unity_endfield_graph_shader_lab/tools/character_dynamics_telemetry.py \
        --target chen-overview --start-immediately

After attaching without ``--start-immediately``, create the printed empty
``.start-character-dynamics`` file immediately before opening the target
overview.  Stop with Ctrl+C.  Normal Frida attach refusal is terminal; this
tool never retries through protection or uses an injector.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.story_recovery import runtime_trace_core as core  # noqa: E402


DEFAULT_MANIFEST = ROOT / "unity_endfield_graph_shader_lab/config/character_dynamics_telemetry_hooks.json"
DEFAULT_AGENT = SCRIPT_DIR / "character_dynamics_telemetry_agent.js"
EVENT_SCHEMA = "characterDynamicsTelemetry.event.v1"
MANIFEST_SCHEMA = "characterDynamicsTelemetry.hooks.v1"
AGENT_PLACEHOLDER = "__CHARACTER_DYNAMICS_TRACE_CONFIG__"
DEFAULT_OUTPUT_ROOT = ROOT / "scratch/reverse_engineering/character_dynamics_telemetry"

CaptureConfigurationError = core.CaptureConfigurationError


def default_output_path(target: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUTPUT_ROOT / f"{target}-{stamp}.jsonl"


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = core.load_manifest_object(path, MANIFEST_SCHEMA, "character dynamics telemetry")
    for key in ("gameBuild", "processName", "moduleName"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            raise CaptureConfigurationError(f"manifest {key} must be a non-empty string")
    files = manifest.get("files")
    hooks = manifest.get("hooks")
    targets = manifest.get("targets")
    capture = manifest.get("capture")
    if not isinstance(files, dict) or not files:
        raise CaptureConfigurationError("manifest files must be a non-empty object")
    if not isinstance(hooks, dict) or not hooks:
        raise CaptureConfigurationError("manifest hooks must be a non-empty object")
    if not isinstance(targets, dict) or not targets:
        raise CaptureConfigurationError("manifest targets must be a non-empty object")
    if not isinstance(capture, dict):
        raise CaptureConfigurationError("manifest capture must be an object")
    for name, spec in hooks.items():
        if not isinstance(spec, dict):
            raise CaptureConfigurationError(f"hook {name!r} must be an object")
        for key in ("type", "method", "rva", "expectedBytes"):
            if not isinstance(spec.get(key), str) or not spec[key].strip():
                raise CaptureConfigurationError(f"hook {name!r} {key} must be non-empty")
        try:
            if int(spec["rva"], 16) <= 0:
                raise ValueError
        except ValueError as exc:
            raise CaptureConfigurationError(f"hook {name!r} rva is not hexadecimal") from exc
        expected = spec["expectedBytes"]
        if len(expected) % 2 or any(ch not in "0123456789abcdefABCDEF" for ch in expected):
            raise CaptureConfigurationError(f"hook {name!r} expectedBytes is not hexadecimal")
        snapshots = spec.get("snapshotRegisters", [])
        if not isinstance(snapshots, list) or any(
            register not in {"rcx", "rdx", "r8", "r9"} for register in snapshots
        ):
            raise CaptureConfigurationError(f"hook {name!r} snapshotRegisters is invalid")
        max_reads = capture.get("maxPointerReadsPerEvent")
        if isinstance(max_reads, int) and len(snapshots) > max_reads:
            raise CaptureConfigurationError(f"hook {name!r} exceeds maxPointerReadsPerEvent")
    for target, spec in targets.items():
        if not isinstance(spec, dict) or not isinstance(spec.get("actor"), str):
            raise CaptureConfigurationError(f"target {target!r} must include actor")
    for key in ("maxEvents", "batchSize", "flushIntervalMs", "readBytesPerPointer", "maxPointerReadsPerEvent"):
        value = capture.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise CaptureConfigurationError(f"capture {key} must be a positive integer")
    snapshot_registers = capture.get("snapshotRegisters")
    if not isinstance(snapshot_registers, list) or any(
        register not in {"rcx", "rdx", "r8", "r9"} for register in snapshot_registers
    ):
        raise CaptureConfigurationError("capture snapshotRegisters must name only general registers")
    if len(snapshot_registers) > capture["maxPointerReadsPerEvent"]:
        raise CaptureConfigurationError("capture snapshotRegisters exceeds maxPointerReadsPerEvent")
    return manifest


def render_agent_source(path: Path, manifest: dict[str, Any]) -> str:
    return core.render_agent_template(
        path,
        AGENT_PLACEHOLDER,
        {
            "gameBuild": manifest["gameBuild"],
            "moduleName": manifest["moduleName"],
            "hooks": manifest["hooks"],
            "capture": manifest["capture"],
        },
        "character dynamics telemetry",
    )


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--game-root", type=Path, default=core.DEFAULT_GAME_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--agent", type=Path, default=DEFAULT_AGENT)
    parser.add_argument("--target", required=True, help="manifest target, e.g. chen-overview")
    parser.add_argument("--process", help="process name override")
    parser.add_argument("--pid", type=int, help="attach once to this verified PID")
    parser.add_argument("--output", type=Path, help="JSONL output path")
    parser.add_argument("--wait-seconds", type=float, default=900.0)
    parser.add_argument("--duration", type=float, help="capture duration after the start trigger")
    parser.add_argument("--start-immediately", action="store_true")
    parser.add_argument("--check-only", action="store_true")


def run_capture(
    args: argparse.Namespace,
    manifest: dict[str, Any],
    agent_source: str,
    verified: dict[str, Path],
) -> int:
    try:
        frida = core.load_frida()
    except CaptureConfigurationError:
        raise
    process_name = args.process or manifest["processName"]
    device = frida.get_local_device()
    process = (
        core.process_from_verified_pid(device, args.pid, process_name)
        if args.pid is not None
        else core.find_process(device, process_name, args.wait_seconds)
    )
    output = (args.output or default_output_path(args.target)).resolve()
    start = time.perf_counter()
    session_id = f"{manifest['gameBuild']}-{args.target}-{process.pid}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    writer = core.EventWriter(output, session_id, start, EVENT_SCHEMA)
    target = manifest["targets"][args.target]
    writer.emit(
        "session_start",
        {
            "gameBuild": manifest["gameBuild"],
            "captureTool": f"frida-character-dynamics-telemetry/{getattr(frida, '__version__', 'unknown')}",
            "targetId": args.target,
            "target": target,
            "exportFingerprint": manifest["files"]["metadata"]["sha256"],
            "nativeEvidenceBoundary": manifest["evidenceBoundary"],
        },
    )

    stop = threading.Event()
    ready = threading.Event()
    ready_payload: dict[str, Any] = {}
    fatal: list[dict[str, Any]] = []
    session = None
    script = None

    def on_message(message: dict[str, Any], data: bytes | None) -> None:
        if message.get("type") == "error":
            writer.diagnostic("agent_error", {"message": message, "dataBytes": len(data or b"")})
            fatal.append({"kind": "agent_error", "message": message})
            stop.set()
            return
        payload = message.get("payload")
        if not isinstance(payload, dict):
            writer.diagnostic("unexpected_agent_message", {"message": message})
            return
        channel = payload.get("channel")
        if channel == "ready" and isinstance(payload.get("ready"), dict):
            ready_payload.update(payload["ready"])
            ready.set()
        elif channel == "events" and isinstance(payload.get("events"), list):
            for raw in payload["events"]:
                if not isinstance(raw, dict) or not isinstance(raw.get("kind"), str):
                    writer.diagnostic("invalid_event", {"event": raw})
                    continue
                event = dict(raw)
                kind = event.pop("kind")
                writer.emit(kind, event)
        elif channel == "diagnostic" and isinstance(payload.get("diagnostic"), dict):
            diagnostic = dict(payload["diagnostic"])
            writer.diagnostic(str(diagnostic.pop("kind", "agent_diagnostic")), diagnostic)
        elif channel == "fatal" and isinstance(payload.get("fatal"), dict):
            value = dict(payload["fatal"])
            fatal.append(value)
            writer.diagnostic("agent_fatal", value)
            ready.set()
        else:
            writer.diagnostic("unexpected_agent_payload", {"payload": payload})

    def on_detached(*values: Any) -> None:
        writer.diagnostic("session_detached", {"values": [str(value) for value in values]})
        stop.set()

    previous_sigint = core.install_stop_signal(stop)
    trigger_path = output.with_name(f"{output.stem}.start-character-dynamics")
    started = False
    deadline: float | None = None
    try:
        print(f"Attaching read-only character dynamics hooks to {process.name} (PID {process.pid})...", flush=True)
        try:
            session = device.attach(process.pid)
        except Exception as exc:
            writer.diagnostic("attach_refused", {"processName": process.name, "pid": process.pid, "error": str(exc)})
            raise RuntimeError(f"normal Frida attach was refused for PID {process.pid}: {exc}") from exc
        session.on("detached", on_detached)
        core.wait_for_modules(session, [manifest["moduleName"]])
        script = session.create_script(agent_source, name="character-dynamics-telemetry")
        script.on("message", on_message)
        script.load()
        if not ready.wait(15):
            raise RuntimeError("character dynamics agent did not report ready within 15 seconds")
        if fatal:
            raise RuntimeError(f"character dynamics hook refused its target bytes: {fatal[0]}")
        module_facts = core.validate_attached_module(ready_payload, verified["gameAssembly"])
        failed = ready_payload.get("failed") or []
        if failed or any(state != "attached" for state in (ready_payload.get("hooks") or {}).values()):
            raise RuntimeError(f"one or more character dynamics hooks failed to attach: {failed or ready_payload.get('hooks')}")
        writer.emit("native_module_verified", module_facts)
        print(
            f"Verified {manifest['gameBuild']} and attached all {len(ready_payload.get('hooks') or {})} hooks.\n"
            f"Target: {args.target} ({target['actor']})\n"
            f"Output: {output}\nDiagnostics: {writer.diagnostics}\n",
            flush=True,
        )
        if args.start_immediately:
            script.post({"type": "start_capture"})
            writer.emit("capture_started", {"targetId": args.target, "trigger": "command_line"})
            started = True
            deadline = time.monotonic() + args.duration if args.duration is not None else None
        else:
            print(
                "Open the target's CharInfo overview immediately after creating this empty trigger file:\n"
                f"  {trigger_path}\nPress Ctrl+C to stop.",
                flush=True,
            )
        while not stop.wait(0.25):
            if not started and trigger_path.is_file():
                script.post({"type": "start_capture"})
                writer.emit("capture_started", {"targetId": args.target, "trigger": str(trigger_path)})
                started = True
                deadline = time.monotonic() + args.duration if args.duration is not None else None
                print(f"Character dynamics capture started for {args.target}.", flush=True)
            if started and deadline is not None and time.monotonic() >= deadline:
                break
        if script is not None and started:
            script.post({"type": "stop_capture"})
            # Let the agent's bounded batch and stop diagnostic cross the
            # Frida message queue before unloading the script.
            time.sleep(0.25)
        writer.emit("session_end", {"captureStarted": started})
    finally:
        core.restore_stop_signal(previous_sigint)
        if script is not None:
            try:
                script.unload()
            except Exception:
                pass
        if session is not None:
            try:
                session.detach()
            except Exception:
                pass
        writer.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest.resolve())
        if args.target not in manifest["targets"]:
            raise CaptureConfigurationError(
                f"unknown target {args.target!r}; available: {', '.join(sorted(manifest['targets']))}"
            )
        verified = core.verify_game_files(args.game_root.resolve(), manifest)
        agent_source = render_agent_source(args.agent.resolve(), manifest)
        print(
            f"Verified {manifest['gameBuild']}: "
            + ", ".join(f"{name}={path.name}" for name, path in verified.items()),
            flush=True,
        )
        if args.check_only:
            print(f"Hook manifest and agent are ready ({len(agent_source):,} rendered bytes).")
            return 0
        return run_capture(args, manifest, agent_source, verified)
    except (CaptureConfigurationError, TimeoutError, RuntimeError, OSError, ValueError) as exc:
        print(f"Character dynamics telemetry failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
