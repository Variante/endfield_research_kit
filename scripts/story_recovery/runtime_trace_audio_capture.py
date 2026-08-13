r"""Audio capture adapter for :mod:`runtime_trace`.

This is deliberately separate from the mission trace. It reuses the mission
trace launcher only for file verification, process selection, Frida loading,
and module waiting; its manifest, agent, event schema, and evidence boundary
are audio-specific.

Run from the repository root with the repo-local Frida environment::

    tools\frida-runtime\venv\Scripts\python.exe \
        scripts\story_recovery\runtime_trace.py capture --profile audio

The capture is read-only. It records authored carrier calls, AudioAdapter
requests, and playing-id controls; it does not change arguments or prevent
playback.
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

from scripts.story_recovery import runtime_trace_core as core


DEFAULT_GAME_ROOT = core.DEFAULT_GAME_ROOT
DEFAULT_MANIFEST = SCRIPT_DIR / "audio_runtime_trace_hooks.json"
DEFAULT_AGENT = SCRIPT_DIR / "audio_runtime_trace_agent.js"
EVENT_SCHEMA = "audioRuntimeTrace.event.v1"
MANIFEST_SCHEMA = "audioRuntimeTrace.hooks.v1"
AUDIO_AGENT_PLACEHOLDER = "__AUDIO_TRACE_CONFIG__"


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--agent", type=Path, default=DEFAULT_AGENT)
    parser.add_argument("--process")
    parser.add_argument("--pid", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--wait-seconds", type=float, default=900.0)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--check-only", action="store_true")


def default_output_path() -> Path:
    return core.default_capture_output("audio")


def load_manifest(path: Path) -> dict[str, Any]:
    value = core.load_manifest_object(path, MANIFEST_SCHEMA, "audio hook")
    for key in ("gameBuild", "processName", "moduleName"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise core.CaptureConfigurationError(f"manifest {key} must be a non-empty string")
    files = value.get("files")
    if not isinstance(files, dict) or not files:
        raise core.CaptureConfigurationError("audio manifest must contain a non-empty files object")
    for required in ("executable", "gameAssembly", "metadata"):
        if required not in files:
            raise core.CaptureConfigurationError(f"audio manifest is missing files.{required}")
    hooks = value.get("hooks")
    if not isinstance(hooks, list) or not hooks:
        raise core.CaptureConfigurationError("audio manifest hooks must be a non-empty list")
    names: set[str] = set()
    for index, hook in enumerate(hooks):
        if not isinstance(hook, dict):
            raise core.CaptureConfigurationError(f"hooks[{index}] must be an object")
        name = hook.get("name")
        if not isinstance(name, str) or not name.strip() or name in names:
            raise core.CaptureConfigurationError(f"hooks[{index}] has a duplicate/invalid name")
        names.add(name)
        rva = hook.get("rva")
        if not isinstance(rva, str) or not rva.lower().startswith("0x"):
            raise core.CaptureConfigurationError(f"hooks[{index}] has an invalid RVA")
        try:
            if int(rva, 16) < 0:
                raise ValueError
        except ValueError as exc:
            raise core.CaptureConfigurationError(
                f"hooks[{index}] has an invalid RVA: {rva!r}"
            ) from exc
        if hook.get("mode") not in {"carrier", "request", "control"}:
            raise core.CaptureConfigurationError(
                f"hooks[{index}] mode must be carrier, request, or control"
            )
        if not isinstance(hook.get("sourceKind"), str) or not hook["sourceKind"].strip():
            raise core.CaptureConfigurationError(f"hooks[{index}] sourceKind is required")
        if "required" in hook and not isinstance(hook["required"], bool):
            raise core.CaptureConfigurationError(f"hooks[{index}] required must be boolean")
    if not isinstance(value.get("evidenceBoundary"), dict):
        raise core.CaptureConfigurationError("audio manifest evidenceBoundary must be an object")
    return value


def render_agent_source(path: Path, manifest: dict[str, Any]) -> str:
    return core.render_agent_template(
        path,
        AUDIO_AGENT_PLACEHOLDER,
        {
            "gameBuild": manifest["gameBuild"],
            "moduleName": manifest["moduleName"],
            "hooks": manifest["hooks"],
            "evidenceBoundary": manifest["evidenceBoundary"],
        },
        "audio",
    )


def validate_hook_ranges(manifest: dict[str, Any], game_assembly: Path) -> None:
    """Reject stale manifest RVAs before Frida is allowed to attach hooks."""
    try:
        module_size = game_assembly.stat().st_size
    except OSError as exc:
        raise core.CaptureConfigurationError(
            f"cannot stat GameAssembly for audio hook range validation: {game_assembly}"
        ) from exc
    invalid = []
    for hook in manifest["hooks"]:
        rva = int(hook["rva"], 16)
        if rva <= 0 or rva >= module_size:
            invalid.append(f"{hook['name']}={hook['rva']}")
    if invalid:
        raise core.CaptureConfigurationError(
            "audio hook RVA is outside the verified GameAssembly range "
            f"(0x0..0x{module_size - 1:x}): {', '.join(invalid)}"
        )


validate_attached_module = core.validate_attached_module


class AudioEventWriter(core.EventWriter):
    def __init__(self, output: Path, session_id: str, start: float) -> None:
        super().__init__(output, session_id, start, EVENT_SCHEMA)

    @property
    def event_count(self) -> int:
        return self.counts["event"]

    def event(self, kind: str, values: dict[str, Any] | None = None) -> None:
        self.emit(kind, values)


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
    session_id = (
        f"{manifest['gameBuild']}-{process.pid}-"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    writer = AudioEventWriter(output, session_id, start)
    writer.event(
        "session_start",
        {
            "gameBuild": manifest["gameBuild"],
            "captureTool": f"frida-audio-runtime-trace/{getattr(frida, '__version__', 'unknown')}",
            "exportFingerprint": manifest["files"]["metadata"]["sha256"],
            "language": manifest.get("language", ""),
            "expectedModulePath": str(verified["gameAssembly"].resolve()),
            "expectedModuleSize": verified["gameAssembly"].stat().st_size,
            "evidenceBoundary": manifest["evidenceBoundary"],
        },
    )
    stop = threading.Event()
    ready = threading.Event()
    ready_payload: dict[str, Any] = {}
    module_facts: dict[str, Any] = {}
    session = None
    script = None

    def on_message(message: dict[str, Any], data: bytes | None) -> None:
        if message.get("type") == "error":
            writer.diagnostic("agent_error", {"message": message, "dataBytes": len(data or b"")})
            stop.set()
            return
        payload = message.get("payload")
        if not isinstance(payload, dict):
            writer.diagnostic("unexpected_agent_message", {"message": message})
            return
        channel = payload.get("channel")
        if channel == "event" and isinstance(payload.get("event"), dict):
            values = dict(payload["event"])
            kind = values.pop("kind", None)
            if isinstance(kind, str) and kind:
                writer.event(kind, values)
            else:
                writer.diagnostic("event_kind_missing", {"event": payload["event"]})
        elif channel == "diagnostic" and isinstance(payload.get("diagnostic"), dict):
            values = dict(payload["diagnostic"])
            kind = values.pop("kind", "audio_agent_diagnostic")
            writer.diagnostic(str(kind), values)
        elif channel == "ready" and isinstance(payload.get("ready"), dict):
            ready_payload.update(payload["ready"])
            ready.set()
        else:
            writer.diagnostic("unexpected_agent_payload", {"payload": payload})

    def on_detached(*values: Any) -> None:
        writer.diagnostic("session_detached", {"values": [str(value) for value in values]})
        stop.set()

    previous_sigint = core.install_stop_signal(stop)
    try:
        print(f"Attaching read-only audio hooks to {process.name} (PID {process.pid})...", flush=True)
        try:
            session = device.attach(process.pid)
        except Exception as exc:
            writer.diagnostic("attach_refused", {"processName": process.name, "pid": process.pid, "error": str(exc)})
            writer.event("session_end")
            raise RuntimeError(f"normal Frida attach was refused for PID {process.pid}: {exc}") from exc
        session.on("detached", on_detached)
        core.wait_for_modules(session, [manifest["moduleName"]])
        script = session.create_script(agent_source, name="audio-runtime-trace")
        script.on("message", on_message)
        script.load()
        if not ready.wait(15):
            raise RuntimeError("audio hook agent did not report ready within 15 seconds")
        try:
            module_facts = validate_attached_module(ready_payload, verified["gameAssembly"])
        except RuntimeError as exc:
            writer.diagnostic(
                "attached_module_mismatch",
                {
                    "error": str(exc),
                    "expectedModulePath": str(verified["gameAssembly"].resolve()),
                    "expectedModuleSize": verified["gameAssembly"].stat().st_size,
                    "attachedModulePath": ready_payload.get("modulePath"),
                    "attachedModuleSize": ready_payload.get("moduleSize"),
                },
            )
            raise
        writer.diagnostic("attached_module_verified", module_facts)
        hooks = ready_payload.get("hooks", {})
        if not isinstance(hooks, dict):
            raise RuntimeError("audio hook agent returned an invalid hook status payload")
        manifest_hooks = {hook["name"]: hook for hook in manifest["hooks"]}
        required_names = {
            name
            for name, hook in manifest_hooks.items()
            if hook.get("required", name == "AudioAdapter._PostEvent")
        }
        failed = {
            name: hooks.get(name, "missing")
            for name in sorted(required_names)
            if hooks.get(name) != "attached"
        }
        optional_failed = {
            name: state
            for name, state in hooks.items()
            if state != "attached" and name not in required_names
        }
        if optional_failed:
            writer.diagnostic("optional_audio_hook_failed", {"hooks": optional_failed})
        if failed:
            raise RuntimeError(f"one or more audio hooks failed to attach: {failed}")
        attached_count = sum(state == "attached" for state in hooks.values())
        optional_failure_text = (
            f"Optional hook failures: {optional_failed}\n" if optional_failed else ""
        )
        print(
            f"Capture armed: {attached_count}/{len(hooks)} audio hooks attached.\n"
            + optional_failure_text
            + f"Audio events: {output}\nDiagnostics: {writer.diagnostics}\n"
            + "Play through a target scene/skill, then press Ctrl+C to stop.",
            flush=True,
        )
        deadline = time.monotonic() + args.duration if args.duration is not None else None
        while not stop.wait(0.25):
            if deadline is not None and time.monotonic() >= deadline:
                break
        writer.event("session_end", module_facts)
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
    print(
        f"Capture stopped: {writer.event_count} audio events, "
        f"{writer.diagnostic_count} diagnostics -> {output}",
        flush=True,
    )
    return 0


def capture(args: argparse.Namespace) -> int:
    try:
        manifest = load_manifest(args.manifest.resolve())
        verified = core.verify_game_files(args.game_root.resolve(), manifest)
        validate_hook_ranges(manifest, verified["gameAssembly"])
        agent_source = render_agent_source(args.agent.resolve(), manifest)
        print(
            f"Verified {manifest['gameBuild']}: "
            + ", ".join(f"{name}={path.name}" for name, path in verified.items()),
            flush=True,
        )
        if args.check_only:
            print(f"Audio hook manifest and agent are ready ({len(agent_source):,} rendered bytes).")
            return 0
        return run_capture(args, manifest, agent_source, verified)
    except (core.CaptureConfigurationError, TimeoutError, RuntimeError, KeyError) as exc:
        print(f"Audio runtime capture failed: {exc}", file=sys.stderr)
        return 1
