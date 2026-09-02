r"""Mission/LevelScript capture adapter for :mod:`runtime_trace`.

This launcher refuses to load hooks unless the installed executable,
GameAssembly, and IL2CPP metadata exactly match the reviewed hook manifest.
The resulting JSONL is normalized through the maintained ``runtime_trace``
module entry point.

Run from the repository root with the repo-local Frida environment:
    tools\frida-runtime\venv\Scripts\python.exe -m \
        scripts.story_recovery.runtime_trace capture --profile mission
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from . import runtime_trace_core as core

if __package__ == "scripts.story_recovery":
    from ..story_builder.native_contracts.mission_task_paths import (
        MissionTaskPathContractError,
        load_mission_task_paths,
    )
elif __package__ == "story_recovery":
    from story_builder.native_contracts.mission_task_paths import (
        MissionTaskPathContractError,
        load_mission_task_paths,
    )
else:  # pragma: no cover - invalid embedding identity
    raise ImportError(f"unsupported package identity: {__package__!r}")

ROOT = core.ROOT
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_GAME_ROOT = core.DEFAULT_GAME_ROOT
DEFAULT_MANIFEST = SCRIPT_DIR / "mission_runtime_trace_hooks.json"
DEFAULT_AGENT = SCRIPT_DIR / "mission_runtime_trace_agent.js"
DEFAULT_SHADER_MANIFEST = (
    ROOT / "endfield_reconstruction_lab" / "config" / "shader_runtime_trace_hooks.json"
)
DEFAULT_SHADER_AGENT = (
    ROOT / "endfield_reconstruction_lab" / "tools" / "shader_runtime_trace_agent.js"
)
EVENT_SCHEMA = "missionRuntimeTrace.event.v1"
MANIFEST_SCHEMA = "missionRuntimeTrace.hooks.v2"
AGENT_PLACEHOLDER = "__MISSION_TRACE_CONFIG__"
SHADER_EVENT_SCHEMA = "shaderRuntimeTrace.event.v1"
SHADER_MANIFEST_SCHEMA = "shaderRuntimeTrace.hooks.v1"
SHADER_AGENT_PLACEHOLDER = "__SHADER_TRACE_CONFIG__"


CaptureConfigurationError = core.CaptureConfigurationError


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--agent", type=Path, default=DEFAULT_AGENT)
    parser.add_argument("--shader-manifest", type=Path, default=DEFAULT_SHADER_MANIFEST)
    parser.add_argument("--shader-agent", type=Path, default=DEFAULT_SHADER_AGENT)
    parser.add_argument("--shader-target", default="wulfa-settled")
    parser.add_argument(
        "--shader-start-immediately",
        action="store_true",
        help="start shader sampling at attach instead of waiting for the trigger file",
    )
    parser.add_argument(
        "--no-shader-hooks",
        action="store_true",
        help="capture only Mission/Story events",
    )
    parser.add_argument("--process", help="process name override; defaults to the manifest")
    parser.add_argument(
        "--pid",
        type=int,
        help="attach once to this PID after tasklist verifies the expected image name",
    )
    parser.add_argument("--output", type=Path, help="capture JSONL path")
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=900.0,
        help="how long to wait for the game process (default: 900)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        help="optional capture duration in seconds after attaching",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate hashes and render the agent without attaching",
    )


def default_output_path() -> Path:
    return core.default_capture_output("mission")


def load_manifest(path: Path) -> dict[str, Any]:
    value = core.load_manifest_object(path, MANIFEST_SCHEMA, "mission hook")
    if not isinstance(value.get("files"), dict) or not isinstance(value.get("hooks"), dict):
        raise CaptureConfigurationError("manifest must contain files and hooks objects")
    for key in ("gameBuild", "processName", "moduleName"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise CaptureConfigurationError(f"manifest {key} must be a non-empty string")
    contract_ref = value.get("missionTaskPathsContract")
    if not isinstance(contract_ref, str) or not contract_ref.strip():
        raise CaptureConfigurationError(
            "manifest missionTaskPathsContract must be a non-empty relative path"
        )
    if Path(contract_ref).is_absolute():
        raise CaptureConfigurationError(
            "manifest missionTaskPathsContract must be relative to the manifest"
        )
    if "levelScriptTask" in value["hooks"]:
        raise CaptureConfigurationError(
            "manifest must reference the canonical mission task-path contract; "
            "embedded hooks.levelScriptTask is not allowed"
        )
    contract_path = (path.resolve().parent / contract_ref).resolve()
    try:
        contract = load_mission_task_paths(contract_path)
    except MissionTaskPathContractError as exc:
        raise CaptureConfigurationError(str(exc)) from exc
    if contract["gameBuild"] != value["gameBuild"]:
        raise CaptureConfigurationError(
            "mission task-path contract targets a different game build: "
            f"manifest={value['gameBuild']!r} contract={contract['gameBuild']!r}"
        )
    value["hooks"] = {
        **value["hooks"],
        "levelScriptTask": contract["hooks"],
    }
    value["missionTaskPathsContractSha256"] = contract["sha256"]
    return value


def load_shader_manifest(path: Path, target_id: str) -> dict[str, Any]:
    value = core.load_manifest_object(path, SHADER_MANIFEST_SCHEMA, "shader hook")
    if not isinstance(value.get("files"), dict) or not isinstance(value.get("hook"), dict):
        raise CaptureConfigurationError("shader manifest must contain files and hook objects")
    targets = value.get("targets")
    if not isinstance(targets, dict) or not isinstance(targets.get(target_id), dict):
        available = ", ".join(sorted(targets)) if isinstance(targets, dict) else "none"
        raise CaptureConfigurationError(
            f"unknown shader target {target_id!r}; available targets: {available}"
        )
    return value

verify_game_files = core.verify_game_files


def render_agent_source(path: Path, manifest: dict[str, Any]) -> str:
    return core.render_agent_template(
        path,
        AGENT_PLACEHOLDER,
        {
            "gameBuild": manifest["gameBuild"],
            "moduleName": manifest["moduleName"],
            "hooks": manifest["hooks"],
        },
        "mission",
    )


def render_shader_agent_source(
    path: Path,
    manifest: dict[str, Any],
    target_id: str,
) -> str:
    return core.render_agent_template(
        path,
        SHADER_AGENT_PLACEHOLDER,
        {
            "gameBuild": manifest["gameBuild"],
            "moduleName": manifest["moduleName"],
            "hook": manifest["hook"],
            "capture": manifest["capture"],
            "targetId": target_id,
            "target": manifest["targets"][target_id],
            "evidenceBoundary": manifest["evidenceBoundary"],
        },
        "shader",
    )


def diagnostics_path(output: Path) -> Path:
    return core.diagnostics_path(output)


def shader_output_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.shader.jsonl")


def shader_trigger_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.start-shader")


class EventWriter(core.EventWriter):
    def __init__(self, output: Path, session_id: str, start: float) -> None:
        self.shader_output = shader_output_path(output)
        super().__init__(
            output,
            session_id,
            start,
            EVENT_SCHEMA,
            {"shader": (self.shader_output, SHADER_EVENT_SCHEMA)},
        )

    @property
    def event_count(self) -> int:
        return self.counts["event"]

    @property
    def shader_event_count(self) -> int:
        return self.counts["shader"]

    def event(self, kind: str, values: dict[str, Any] | None = None) -> None:
        self.emit(kind, values)

    def shader_event(self, kind: str, values: dict[str, Any] | None = None) -> None:
        self.emit(kind, values, channel="shader")


find_process = core.find_process
process_from_verified_pid = core.process_from_verified_pid
load_frida = core.load_frida
wait_for_modules = core.wait_for_modules


def run_capture(
    args: argparse.Namespace,
    manifest: dict[str, Any],
    agent_source: str,
    shader_manifest: dict[str, Any] | None,
    shader_agent_source: str | None,
) -> int:
    frida = load_frida()
    process_name = args.process or manifest["processName"]
    device = frida.get_local_device()
    process = (
        process_from_verified_pid(device, args.pid, process_name)
        if args.pid is not None
        else find_process(device, process_name, args.wait_seconds)
    )
    output = (args.output or default_output_path()).resolve()
    start = time.perf_counter()
    session_id = f"{manifest['gameBuild']}-{process.pid}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    writer = EventWriter(output, session_id, start)
    writer.event(
        "session_start",
        {
            "gameBuild": manifest["gameBuild"],
            "captureTool": f"frida-runtime-trace/{getattr(frida, '__version__', 'unknown')}",
            "exportFingerprint": manifest["files"]["metadata"]["sha256"],
        },
    )
    if shader_manifest is not None:
        writer.shader_event(
            "session_start",
            {
                "gameBuild": shader_manifest["gameBuild"],
                "captureTool": f"frida-runtime-trace/{getattr(frida, '__version__', 'unknown')}",
                "targetId": args.shader_target,
                "target": shader_manifest["targets"][args.shader_target],
                "evidenceBoundary": shader_manifest["evidenceBoundary"],
            },
        )

    stop = threading.Event()
    ready = threading.Event()
    shader_ready = threading.Event()
    ready_payload: dict[str, Any] = {}
    shader_ready_payload: dict[str, Any] = {}
    shader_fatal: dict[str, Any] = {}
    shader_started = False
    session = None
    script = None
    shader_script = None

    def on_message(message: dict[str, Any], data: bytes | None) -> None:
        if message.get("type") == "error":
            writer.diagnostic("agent_error", {"message": message, "dataBytes": len(data or b"")})
            print(f"Hook agent error: {message.get('description', message)}", file=sys.stderr, flush=True)
            stop.set()
            return
        payload = message.get("payload")
        if not isinstance(payload, dict):
            writer.diagnostic("unexpected_agent_message", {"message": message})
            return
        channel = payload.get("channel")
        if channel == "event" and isinstance(payload.get("event"), dict):
            event = dict(payload["event"])
            kind = event.pop("kind", None)
            if not isinstance(kind, str) or not kind:
                writer.diagnostic("event_kind_missing", {"event": payload["event"]})
                return
            writer.event(kind, event)
        elif channel == "diagnostic" and isinstance(payload.get("diagnostic"), dict):
            diagnostic = dict(payload["diagnostic"])
            kind = diagnostic.pop("kind", "agent_diagnostic")
            writer.diagnostic(str(kind), diagnostic)
        elif channel == "ready" and isinstance(payload.get("ready"), dict):
            ready_payload.update(payload["ready"])
            ready.set()
        elif channel == "shader_events" and isinstance(payload.get("events"), list):
            for raw_event in payload["events"]:
                if not isinstance(raw_event, dict):
                    writer.diagnostic("invalid_shader_event", {"event": raw_event})
                    continue
                event = dict(raw_event)
                kind = event.pop("kind", None)
                if not isinstance(kind, str) or not kind:
                    writer.diagnostic("shader_event_kind_missing", {"event": raw_event})
                    continue
                writer.shader_event(kind, event)
        elif channel == "shader_diagnostic" and isinstance(payload.get("diagnostic"), dict):
            diagnostic = dict(payload["diagnostic"])
            kind = diagnostic.pop("kind", "shader_agent_diagnostic")
            writer.diagnostic(f"shader_{kind}", diagnostic)
        elif channel == "shader_ready" and isinstance(payload.get("ready"), dict):
            shader_ready_payload.update(payload["ready"])
            shader_ready.set()
        elif channel == "shader_fatal" and isinstance(payload.get("fatal"), dict):
            shader_fatal.update(payload["fatal"])
            writer.diagnostic("shader_fatal", shader_fatal)
            shader_ready.set()
        else:
            writer.diagnostic("unexpected_agent_payload", {"payload": payload})

    def on_detached(*values: Any) -> None:
        writer.diagnostic("session_detached", {"values": [str(value) for value in values]})
        stop.set()

    previous_sigint = core.install_stop_signal(stop)
    try:
        print(f"Attaching read-only trace hooks to {process.name} (PID {process.pid})...", flush=True)
        try:
            session = device.attach(process.pid)
        except Exception as exc:
            writer.diagnostic(
                "attach_refused",
                {"processName": process.name, "pid": process.pid, "error": str(exc)},
            )
            writer.event("session_end")
            if shader_manifest is not None:
                writer.shader_event("session_end")
            raise RuntimeError(
                core.describe_attach_refusal(process.name, process.pid, exc)
            ) from exc
        session.on("detached", on_detached)
        required_modules = [manifest["moduleName"]]
        if shader_manifest is not None:
            required_modules.append(shader_manifest["moduleName"])
        wait_for_modules(session, required_modules)
        script = session.create_script(agent_source, name="mission-runtime-trace")
        script.on("message", on_message)
        script.load()
        if shader_agent_source is not None:
            shader_script = session.create_script(shader_agent_source, name="shader-runtime-trace")
            shader_script.on("message", on_message)
            shader_script.load()
        if not ready.wait(15):
            raise RuntimeError("mission hook agent did not report ready within 15 seconds")
        if shader_agent_source is not None and not shader_ready.wait(15):
            raise RuntimeError("shader hook agent did not report ready within 15 seconds")
        if shader_fatal:
            raise RuntimeError(f"shader hook refused its target bytes: {shader_fatal}")
        hooks = ready_payload.get("hooks", {})
        failed = {name: state for name, state in hooks.items() if state != "attached"}
        if failed:
            raise RuntimeError(f"one or more hooks failed to attach: {failed}")
        print(
            f"Capture armed: {len(hooks)} mission hooks attached"
            + (f" plus shader hook {shader_ready_payload.get('hookRva')};" if shader_agent_source else ";")
            + " play through missions or open the configured Character Info target.\n"
            f"Mission events: {output}\nShader events: {writer.shader_output}\n"
            f"Diagnostics: {writer.diagnostics}\nPress Ctrl+C to stop.",
            flush=True,
        )
        trigger_path = shader_trigger_path(output)
        if shader_script is not None:
            if args.shader_start_immediately:
                shader_script.post({"type": "start_shader_capture"})
                shader_started = True
                writer.shader_event("capture_started", {"targetId": args.shader_target})
            else:
                print(
                    "Shader sampling is gated to avoid filling the pair cap during startup.\n"
                    f"When {args.shader_target} is settled, create this empty trigger file:\n"
                    f"{trigger_path}",
                    flush=True,
                )
        deadline = time.monotonic() + args.duration if args.duration is not None else None
        while not stop.wait(0.25):
            if shader_script is not None and not shader_started and trigger_path.is_file():
                shader_script.post({"type": "start_shader_capture"})
                shader_started = True
                writer.shader_event("capture_started", {"targetId": args.shader_target})
                print(f"Shader sampling started for {args.shader_target}.", flush=True)
            if deadline is not None and time.monotonic() >= deadline:
                break
        writer.event("session_end")
        if shader_manifest is not None:
            if shader_script is not None and shader_started:
                shader_script.post({"type": "stop_shader_capture"})
            writer.shader_event("session_end")
    finally:
        core.restore_stop_signal(previous_sigint)
        if shader_script is not None:
            try:
                shader_script.unload()
            except Exception:
                pass
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
        f"Capture stopped: {writer.event_count} mission events, "
        f"{writer.shader_event_count} shader events, "
        f"{writer.diagnostic_count} diagnostics -> {output}",
        flush=True,
    )
    return 0


def capture(args: argparse.Namespace) -> int:
    try:
        manifest_path = args.manifest.resolve()
        agent_path = args.agent.resolve()
        manifest = load_manifest(manifest_path)
        verified = verify_game_files(args.game_root.resolve(), manifest)
        agent_source = render_agent_source(agent_path, manifest)
        shader_manifest = None
        shader_agent_source = None
        shader_verified: dict[str, Path] = {}
        if not args.no_shader_hooks:
            shader_manifest = load_shader_manifest(
                args.shader_manifest.resolve(), args.shader_target
            )
            if shader_manifest["gameBuild"] != manifest["gameBuild"]:
                raise CaptureConfigurationError(
                    "mission and shader hook manifests target different game builds"
                )
            shader_verified = verify_game_files(args.game_root.resolve(), shader_manifest)
            shader_agent_source = render_shader_agent_source(
                args.shader_agent.resolve(), shader_manifest, args.shader_target
            )
        print(
            f"Verified {manifest['gameBuild']}: "
            + ", ".join(f"{name}={path.name}" for name, path in verified.items()),
            flush=True,
        )
        if shader_manifest is not None:
            print(
                f"Verified shader target {args.shader_target}: "
                + ", ".join(f"{name}={path.name}" for name, path in shader_verified.items()),
                flush=True,
            )
        if args.check_only:
            shader_size = len(shader_agent_source or "")
            print(
                f"Hook manifests and agents are ready "
                f"({len(agent_source):,} mission + {shader_size:,} shader rendered bytes)."
            )
            return 0
        return run_capture(
            args,
            manifest,
            agent_source,
            shader_manifest,
            shader_agent_source,
        )
    except (CaptureConfigurationError, TimeoutError, RuntimeError) as exc:
        print(f"Mission runtime capture failed: {exc}", file=sys.stderr)
        return 1
