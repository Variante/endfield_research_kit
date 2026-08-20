"""Capture a bounded, read-only Burst resolver API trace from the retail client.

The probe reuses the shared runtime-trace process, hash gate, EventWriter, and
Frida loading infrastructure used by ``character_dynamics_telemetry.py``.
It only observes ``kernel32!LoadLibraryW`` and ``kernel32!GetProcAddress``;
it never calls a returned pointer or changes game state.

Examples from the repository root::

    python unity_endfield_graph_shader_lab/tools/burst_resolver_telemetry.py \
        --check-only --game-root "D:\\Program Files\\Endfield Game"
    tools\\frida-runtime\\venv\\Scripts\\python.exe \
        unity_endfield_graph_shader_lab/tools/burst_resolver_telemetry.py \
        --start-immediately

Normal Frida attach refusal is terminal.  No injector, protection bypass, or
retry path is provided.
"""
from __future__ import annotations

import argparse
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

from scripts.common import check_installed_native_inputs  # noqa: E402
from scripts.story_recovery import runtime_trace_core as core  # noqa: E402


DEFAULT_MANIFEST = ROOT / "unity_endfield_graph_shader_lab/config/burst_resolver_telemetry_hooks.json"
DEFAULT_AGENT = SCRIPT_DIR / "burst_resolver_telemetry_agent.js"
EVENT_SCHEMA = "burstResolverTelemetry.event.v1"
MANIFEST_SCHEMA = "burstResolverTelemetry.hooks.v1"
AGENT_PLACEHOLDER = "__BURST_RESOLVER_TRACE_CONFIG__"
DEFAULT_OUTPUT_ROOT = ROOT / "scratch/reverse_engineering/burst_resolver_telemetry"

CaptureConfigurationError = core.CaptureConfigurationError


def verify_pinned_native_gate(game_root: Path, manifest: dict[str, Any]) -> Any:
    """Require the shared explicit GameAssembly/metadata hash gate."""

    gameassembly = (game_root / manifest["files"]["gameAssembly"]["relativePath"]).resolve()
    metadata = (game_root / manifest["files"]["metadata"]["relativePath"]).resolve()
    result = check_installed_native_inputs(
        manifest["files"]["gameAssembly"]["sha256"],
        manifest["files"]["metadata"]["sha256"],
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if not result.validated:
        raise CaptureConfigurationError(
            "common.check_installed_native_inputs "
            f"[{result.status}]: {result.detail}"
        )
    if Path(result.gameassembly).resolve() != gameassembly or Path(result.metadata).resolve() != metadata:
        raise CaptureConfigurationError(
            "common.check_installed_native_inputs did not retain the explicit native paths"
        )
    return result


def verified_file_facts(verified: dict[str, Path]) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "path": str(path.resolve()),
            "bytes": path.stat().st_size,
            "sha256": core.sha256_file(path),
        }
        for name, path in verified.items()
    }


def default_output_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUTPUT_ROOT / f"burst-resolver-{stamp}.jsonl"


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = core.load_manifest_object(path, MANIFEST_SCHEMA, "Burst resolver telemetry")
    for key in ("gameBuild", "processName", "moduleName", "kernel32ModuleName", "resolverModuleName"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            raise CaptureConfigurationError(f"manifest {key} must be a non-empty string")
    if manifest["moduleName"].casefold() != "gameassembly.dll":
        raise CaptureConfigurationError("manifest moduleName must be GameAssembly.dll")
    if manifest["kernel32ModuleName"].casefold() != "kernel32.dll":
        raise CaptureConfigurationError("manifest kernel32ModuleName must be kernel32.dll")
    if manifest["resolverModuleName"].casefold() != "lib_burst_generated.dll":
        raise CaptureConfigurationError(
            "manifest resolverModuleName must be lib_burst_generated.dll"
        )

    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != {"executable", "gameAssembly", "metadata"}:
        raise CaptureConfigurationError(
            "manifest files must contain exactly executable, gameAssembly, and metadata"
        )
    for name, spec in files.items():
        if not isinstance(spec, dict):
            raise CaptureConfigurationError(f"manifest file {name!r} must be an object")
        if not isinstance(spec.get("relativePath"), str) or not spec["relativePath"]:
            raise CaptureConfigurationError(f"manifest file {name!r} relativePath is invalid")
        if isinstance(spec.get("bytes"), bool) or not isinstance(spec.get("bytes"), int) or spec["bytes"] <= 0:
            raise CaptureConfigurationError(f"manifest file {name!r} bytes is invalid")
        digest = spec.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in digest):
            raise CaptureConfigurationError(f"manifest file {name!r} sha256 is invalid")

    hooks = manifest.get("hooks")
    if not isinstance(hooks, dict) or set(hooks) != {"loadLibraryW", "getProcAddress"}:
        raise CaptureConfigurationError(
            "manifest hooks must contain exactly loadLibraryW and getProcAddress"
        )
    for name, spec in hooks.items():
        if not isinstance(spec, dict):
            raise CaptureConfigurationError(f"hook {name!r} must be an object")
        hook_module = spec.get("moduleName")
        if not isinstance(hook_module, str) or hook_module.casefold() != manifest["kernel32ModuleName"].casefold():
            raise CaptureConfigurationError(f"hook {name!r} must target kernel32.dll")
        if not isinstance(spec.get("export"), str) or not spec["export"].strip():
            raise CaptureConfigurationError(f"hook {name!r} export must be non-empty")
    if hooks["loadLibraryW"]["export"] != "LoadLibraryW" or hooks["getProcAddress"]["export"] != "GetProcAddress":
        raise CaptureConfigurationError("manifest hooks must target LoadLibraryW and GetProcAddress")

    capture = manifest.get("capture")
    if not isinstance(capture, dict):
        raise CaptureConfigurationError("manifest capture must be an object")
    for key in ("maxEvents", "batchSize", "flushIntervalMs", "maxLibraryPathChars", "maxProcNameChars", "maxBacktraceFrames"):
        value = capture.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise CaptureConfigurationError(f"capture {key} must be a positive integer")
    if capture["maxEvents"] > 100000 or capture["maxBacktraceFrames"] > 64:
        raise CaptureConfigurationError("capture bounds are too large")
    if capture.get("requireAllHooks") is not True or capture.get("gameAssemblyOnlyBacktrace") is not True:
        raise CaptureConfigurationError("capture must require all hooks and GameAssembly-only backtraces")
    boundary = manifest.get("evidenceBoundary")
    if not isinstance(boundary, dict) or not isinstance(boundary.get("nonClaims"), list) or not boundary["nonClaims"]:
        raise CaptureConfigurationError("manifest evidenceBoundary.nonClaims must be non-empty")
    return manifest


def render_agent_source(path: Path, manifest: dict[str, Any]) -> str:
    return core.render_agent_template(
        path,
        AGENT_PLACEHOLDER,
        {
            "gameBuild": manifest["gameBuild"],
            "moduleName": manifest["moduleName"],
            "kernel32ModuleName": manifest["kernel32ModuleName"],
            "resolverModuleName": manifest["resolverModuleName"],
            "hooks": manifest["hooks"],
            "capture": manifest["capture"],
        },
        "Burst resolver telemetry",
    )


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--game-root", type=Path, default=core.DEFAULT_GAME_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--agent", type=Path, default=DEFAULT_AGENT)
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
    frida = core.load_frida()
    process_name = args.process or manifest["processName"]
    device = frida.get_local_device()
    process = (
        core.process_from_verified_pid(device, args.pid, process_name)
        if args.pid is not None
        else core.find_process(device, process_name, args.wait_seconds)
    )
    output = (args.output or default_output_path()).resolve()
    start = time.perf_counter()
    session_id = f"{manifest['gameBuild']}-burst-resolver-{process.pid}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    writer = core.EventWriter(output, session_id, start, EVENT_SCHEMA)
    file_facts = verified_file_facts(verified)
    writer.emit(
        "session_start",
        {
            "gameBuild": manifest["gameBuild"],
            "captureTool": f"frida-burst-resolver-telemetry/{getattr(frida, '__version__', 'unknown')}",
            "exportFingerprint": manifest["files"]["metadata"]["sha256"],
            "verifiedFiles": file_facts,
            "kernel32ModuleName": manifest["kernel32ModuleName"],
            "resolverModuleName": manifest["resolverModuleName"],
            "nativeEvidenceBoundary": manifest["evidenceBoundary"],
        },
    )

    stop = threading.Event()
    ready = threading.Event()
    ready_payload: dict[str, Any] = {}
    fatal_values: list[dict[str, Any]] = []
    stop_ack = threading.Event()
    terminal_failure = False
    session = None
    script = None

    def on_message(message: dict[str, Any], data: bytes | None) -> None:
        nonlocal terminal_failure
        if message.get("type") == "error":
            value = {"kind": "agent_error", "message": message, "dataBytes": len(data or b"")}
            writer.emit("capture_fatal", value)
            writer.diagnostic("agent_error", value)
            fatal_values.append(value)
            terminal_failure = True
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
            for raw_event in payload["events"]:
                if not isinstance(raw_event, dict) or not isinstance(raw_event.get("kind"), str):
                    writer.diagnostic("invalid_event", {"event": raw_event})
                    continue
                event = dict(raw_event)
                kind = event.pop("kind")
                writer.emit(kind, event)
        elif channel == "diagnostic" and isinstance(payload.get("diagnostic"), dict):
            diagnostic = dict(payload["diagnostic"])
            writer.diagnostic(str(diagnostic.pop("kind", "agent_diagnostic")), diagnostic)
        elif channel == "state" and isinstance(payload.get("state"), dict):
            state = dict(payload["state"])
            kind = str(state.pop("kind", "capture_state"))
            writer.emit(kind, state)
            if kind == "capture_stop_ack":
                stop_ack.set()
            elif kind in {"capture_fatal", "capture_capped", "capture_detached", "capture_start_rejected"}:
                terminal_failure = True
                stop.set()
        elif channel == "fatal" and isinstance(payload.get("fatal"), dict):
            value = dict(payload["fatal"])
            fatal_values.append(value)
            terminal_failure = True
            writer.emit("capture_fatal", value)
            writer.diagnostic("agent_fatal", value)
            stop.set()
            ready.set()
        else:
            writer.diagnostic("unexpected_agent_payload", {"payload": payload})

    def on_detached(*values: Any) -> None:
        nonlocal terminal_failure
        value = {"values": [str(value) for value in values]}
        terminal_failure = True
        writer.emit("capture_detached", value)
        writer.diagnostic("session_detached", value)
        stop.set()

    previous_sigint = core.install_stop_signal(stop)
    trigger_path = output.with_name(f"{output.stem}.start-burst-resolver")
    started = False
    deadline: float | None = None
    try:
        print(f"Attaching read-only Burst resolver hooks to {process.name} (PID {process.pid})...", flush=True)
        try:
            session = device.attach(process.pid)
        except Exception as exc:
            writer.diagnostic("attach_refused", {"processName": process.name, "pid": process.pid, "error": str(exc)})
            raise RuntimeError(f"normal Frida attach was refused for PID {process.pid}: {exc}") from exc
        session.on("detached", on_detached)
        core.wait_for_modules(session, [manifest["moduleName"], manifest["kernel32ModuleName"]])
        script = session.create_script(agent_source, name="burst-resolver-telemetry")
        script.on("message", on_message)
        script.load()
        if not ready.wait(15):
            raise RuntimeError("Burst resolver telemetry agent did not report ready within 15 seconds")
        if fatal_values:
            raise RuntimeError(f"Burst resolver hooks refused to start: {fatal_values[0]}")
        module_facts = core.validate_attached_module(ready_payload, verified["gameAssembly"])
        if ready_payload.get("kernel32ModuleName", "").casefold() != manifest["kernel32ModuleName"].casefold():
            raise RuntimeError("agent did not confirm the expected kernel32 module")
        if ready_payload.get("resolverModuleName", "").casefold() != manifest["resolverModuleName"].casefold():
            raise RuntimeError("agent did not confirm the expected Burst resolver module name")
        hooks = ready_payload.get("hooks")
        failed = ready_payload.get("failed") or []
        if not isinstance(hooks, dict) or set(hooks) != set(manifest["hooks"]):
            raise RuntimeError(f"agent hook handshake is incomplete: {hooks}")
        if failed or any(value != "attached" for value in hooks.values()):
            raise RuntimeError(f"one or more Burst resolver hooks failed to attach: {failed or hooks}")
        writer.emit(
            "native_module_verified",
            {
                **module_facts,
                "verifiedFiles": file_facts,
                "hookStates": hooks,
                "kernel32ModuleName": ready_payload["kernel32ModuleName"],
                "resolverModuleName": ready_payload["resolverModuleName"],
                "resolverModuleIdentity": ready_payload.get("resolverModuleIdentity"),
            },
        )
        if args.start_immediately:
            try:
                script.post({"type": "start_capture"})
            except Exception as exc:
                terminal_failure = True
                writer.diagnostic("capture_start_post_failed", {"error": str(exc)})
                writer.emit("capture_start_rejected", {"reason": "agent_post_failed"})
                stop.set()
            else:
                writer.emit("capture_started", {"trigger": "command_line"})
                started = True
                deadline = time.monotonic() + args.duration if args.duration is not None else None
        else:
            print(
                "Create this empty trigger file to start the bounded resolver trace, then reproduce the target load/resolution:\n"
                f"  {trigger_path}\nPress Ctrl+C to stop.",
                flush=True,
            )
        while not stop.wait(0.25):
            if not started and trigger_path.is_file():
                try:
                    script.post({"type": "start_capture"})
                except Exception as exc:
                    terminal_failure = True
                    writer.diagnostic("capture_start_post_failed", {"error": str(exc)})
                    writer.emit("capture_start_rejected", {"reason": "agent_post_failed"})
                    stop.set()
                else:
                    writer.emit("capture_started", {"trigger": str(trigger_path)})
                    started = True
                    deadline = time.monotonic() + args.duration if args.duration is not None else None
                    print("Burst resolver capture started.", flush=True)
            if started and deadline is not None and time.monotonic() >= deadline:
                break
        if script is not None:
            try:
                script.post({"type": "stop_capture"})
            except Exception as exc:
                terminal_failure = True
                writer.diagnostic("capture_stop_post_failed", {"error": str(exc)})
                writer.emit("capture_stop_ack_missing", {"reason": "agent_post_failed"})
            else:
                if not stop_ack.wait(1.0):
                    terminal_failure = True
                    writer.emit("capture_stop_ack_missing", {})
        if not started:
            terminal_failure = True
            writer.emit("capture_not_started", {})
        writer.emit(
            "session_end",
            {
                "captureStarted": started,
                "stopAck": stop_ack.is_set(),
                "terminalFailure": terminal_failure or bool(fatal_values),
            },
        )
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
    return 1 if terminal_failure or fatal_values else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest.resolve())
        game_root = args.game_root.resolve()
        verify_pinned_native_gate(game_root, manifest)
        verified = core.verify_game_files(game_root, manifest)
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
        print(f"Burst resolver telemetry failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
