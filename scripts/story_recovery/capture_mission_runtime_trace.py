r"""Capture hash-locked Mission/LevelScript runtime observations with Frida.

This launcher refuses to load hooks unless the installed executable,
GameAssembly, and IL2CPP metadata exactly match the reviewed hook manifest.
The resulting JSONL can be normalized by import_mission_runtime_trace.py.

Run from the repository root with the repo-local Frida environment:
    tools\frida-runtime\venv\Scripts\python.exe \
        scripts\story_recovery\capture_mission_runtime_trace.py
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game")
DEFAULT_MANIFEST = SCRIPT_DIR / "mission_runtime_trace_hooks.json"
DEFAULT_AGENT = SCRIPT_DIR / "mission_runtime_trace_agent.js"
DEFAULT_SHADER_MANIFEST = (
    ROOT / "unity_endfield_graph_shader_lab" / "config" / "shader_runtime_trace_hooks.json"
)
DEFAULT_SHADER_AGENT = (
    ROOT / "unity_endfield_graph_shader_lab" / "tools" / "shader_runtime_trace_agent.js"
)
EVENT_SCHEMA = "missionRuntimeTrace.event.v1"
MANIFEST_SCHEMA = "missionRuntimeTrace.hooks.v1"
AGENT_PLACEHOLDER = "__MISSION_TRACE_CONFIG__"
SHADER_EVENT_SCHEMA = "shaderRuntimeTrace.event.v1"
SHADER_MANIFEST_SCHEMA = "shaderRuntimeTrace.hooks.v1"
SHADER_AGENT_PLACEHOLDER = "__SHADER_TRACE_CONFIG__"


class CaptureConfigurationError(RuntimeError):
    """Raised when the local game build or hook configuration is unsafe."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def default_output_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "scratch" / "story" / "runtime_trace" / f"mission-runtime-{stamp}.jsonl"


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CaptureConfigurationError(f"hook manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CaptureConfigurationError(f"invalid hook manifest JSON: {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema") != MANIFEST_SCHEMA:
        raise CaptureConfigurationError(f"manifest schema must be {MANIFEST_SCHEMA!r}")
    if not isinstance(value.get("files"), dict) or not isinstance(value.get("hooks"), dict):
        raise CaptureConfigurationError("manifest must contain files and hooks objects")
    for key in ("gameBuild", "processName", "moduleName"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise CaptureConfigurationError(f"manifest {key} must be a non-empty string")
    return value


def load_shader_manifest(path: Path, target_id: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CaptureConfigurationError(f"shader hook manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CaptureConfigurationError(f"invalid shader hook manifest JSON: {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema") != SHADER_MANIFEST_SCHEMA:
        raise CaptureConfigurationError(f"shader manifest schema must be {SHADER_MANIFEST_SCHEMA!r}")
    if not isinstance(value.get("files"), dict) or not isinstance(value.get("hook"), dict):
        raise CaptureConfigurationError("shader manifest must contain files and hook objects")
    targets = value.get("targets")
    if not isinstance(targets, dict) or not isinstance(targets.get(target_id), dict):
        available = ", ".join(sorted(targets)) if isinstance(targets, dict) else "none"
        raise CaptureConfigurationError(
            f"unknown shader target {target_id!r}; available targets: {available}"
        )
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_game_files(game_root: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    verified: dict[str, Path] = {}
    for name, expected in manifest["files"].items():
        if not isinstance(expected, dict):
            raise CaptureConfigurationError(f"manifest file entry {name!r} must be an object")
        relative_path = expected.get("relativePath")
        expected_size = expected.get("bytes")
        expected_hash = expected.get("sha256")
        if not isinstance(relative_path, str) or not relative_path:
            raise CaptureConfigurationError(f"manifest file {name!r} has no relativePath")
        if isinstance(expected_size, bool) or not isinstance(expected_size, int):
            raise CaptureConfigurationError(f"manifest file {name!r} has invalid bytes")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise CaptureConfigurationError(f"manifest file {name!r} has invalid sha256")
        path = (game_root / Path(relative_path)).resolve()
        if not path.is_file():
            raise CaptureConfigurationError(f"required game file not found: {path}")
        actual_size = path.stat().st_size
        if actual_size != expected_size:
            raise CaptureConfigurationError(
                f"refusing hooks: {name} size changed: expected {expected_size}, got {actual_size}"
            )
        actual_hash = sha256_file(path)
        if actual_hash.lower() != expected_hash.lower():
            raise CaptureConfigurationError(
                f"refusing hooks: {name} SHA-256 changed: expected {expected_hash}, got {actual_hash}"
            )
        verified[name] = path
    return verified


def render_agent_source(path: Path, manifest: dict[str, Any]) -> str:
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CaptureConfigurationError(f"Frida agent not found: {path}") from exc
    if source.count(AGENT_PLACEHOLDER) != 1:
        raise CaptureConfigurationError(
            f"Frida agent must contain exactly one {AGENT_PLACEHOLDER} placeholder"
        )
    config = {
        "gameBuild": manifest["gameBuild"],
        "moduleName": manifest["moduleName"],
        "hooks": manifest["hooks"],
    }
    return source.replace(
        AGENT_PLACEHOLDER,
        json.dumps(config, ensure_ascii=False, separators=(",", ":")),
    )


def render_shader_agent_source(
    path: Path,
    manifest: dict[str, Any],
    target_id: str,
) -> str:
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CaptureConfigurationError(f"shader Frida agent not found: {path}") from exc
    if source.count(SHADER_AGENT_PLACEHOLDER) != 1:
        raise CaptureConfigurationError(
            f"shader Frida agent must contain exactly one {SHADER_AGENT_PLACEHOLDER} placeholder"
        )
    config = {
        "gameBuild": manifest["gameBuild"],
        "moduleName": manifest["moduleName"],
        "hook": manifest["hook"],
        "capture": manifest["capture"],
        "targetId": target_id,
        "target": manifest["targets"][target_id],
        "evidenceBoundary": manifest["evidenceBoundary"],
    }
    return source.replace(
        SHADER_AGENT_PLACEHOLDER,
        json.dumps(config, ensure_ascii=False, separators=(",", ":")),
    )


def diagnostics_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.diagnostics.jsonl")


def shader_output_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.shader.jsonl")


def shader_trigger_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.start-shader")


class EventWriter:
    def __init__(self, output: Path, session_id: str, start: float) -> None:
        self.output = output
        self.diagnostics = diagnostics_path(output)
        self.shader_output = shader_output_path(output)
        self.session_id = session_id
        self.start = start
        self.seq = 0
        self.shader_seq = 0
        self.event_count = 0
        self.shader_event_count = 0
        self.diagnostic_count = 0
        self.lock = threading.Lock()
        output.parent.mkdir(parents=True, exist_ok=True)
        self.event_handle = output.open("w", encoding="utf-8", newline="\n")
        self.shader_handle = self.shader_output.open("w", encoding="utf-8", newline="\n")
        self.diagnostic_handle = self.diagnostics.open("w", encoding="utf-8", newline="\n")

    def _write(self, handle: Any, value: dict[str, Any]) -> None:
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()

    def event(self, kind: str, values: dict[str, Any] | None = None) -> None:
        values = dict(values or {})
        with self.lock:
            row = {
                **values,
                "schema": EVENT_SCHEMA,
                "sessionId": self.session_id,
                "seq": self.seq,
                "monotonicMs": round((time.perf_counter() - self.start) * 1000, 3),
                "utc": utc_now(),
                "kind": kind,
            }
            self._write(self.event_handle, row)
            self.seq += 1
            self.event_count += 1

    def shader_event(self, kind: str, values: dict[str, Any] | None = None) -> None:
        values = dict(values or {})
        with self.lock:
            row = {
                **values,
                "schema": SHADER_EVENT_SCHEMA,
                "sessionId": self.session_id,
                "seq": self.shader_seq,
                "monotonicMs": round((time.perf_counter() - self.start) * 1000, 3),
                "utc": utc_now(),
                "kind": kind,
            }
            self._write(self.shader_handle, row)
            self.shader_seq += 1
            self.shader_event_count += 1

    def diagnostic(self, kind: str, values: dict[str, Any] | None = None) -> None:
        with self.lock:
            row = {
                "utc": utc_now(),
                "monotonicMs": round((time.perf_counter() - self.start) * 1000, 3),
                "sessionId": self.session_id,
                "kind": kind,
                **dict(values or {}),
            }
            self._write(self.diagnostic_handle, row)
            self.diagnostic_count += 1

    def close(self) -> None:
        self.event_handle.close()
        self.shader_handle.close()
        self.diagnostic_handle.close()


def find_process(device: Any, process_name: str, wait_seconds: float) -> Any:
    deadline = time.monotonic() + max(wait_seconds, 0)
    announced = False
    while True:
        matches = [
            process
            for process in device.enumerate_processes()
            if process.name.casefold() == process_name.casefold()
        ]
        if matches:
            if len(matches) > 1:
                raise CaptureConfigurationError(
                    f"multiple {process_name} processes are running; refusing an ambiguous attach"
                )
            return matches[0]
        if time.monotonic() >= deadline:
            raise TimeoutError(f"timed out waiting for {process_name}")
        if not announced:
            print(f"Waiting for {process_name}; start the game normally now...", flush=True)
            announced = True
        time.sleep(0.25)


def process_from_verified_pid(device: Any, pid: int, process_name: str) -> Any:
    if pid <= 0:
        raise CaptureConfigurationError("--pid must be a positive integer")
    for process in device.enumerate_processes():
        if process.pid == pid:
            if process.name.casefold() != process_name.casefold():
                raise CaptureConfigurationError(
                    f"PID {pid} is {process.name!r}, expected {process_name!r}"
                )
            return process
    result = subprocess.run(
        ["tasklist.exe", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    rows = list(csv.reader(io.StringIO(result.stdout)))
    if result.returncode or len(rows) != 1 or len(rows[0]) < 2:
        raise CaptureConfigurationError(f"could not verify Windows process PID {pid}")
    image_name = rows[0][0]
    try:
        listed_pid = int(rows[0][1].replace(",", ""))
    except ValueError as exc:
        raise CaptureConfigurationError(f"tasklist returned an invalid PID row: {rows[0]}") from exc
    if listed_pid != pid or image_name.casefold() != process_name.casefold():
        raise CaptureConfigurationError(
            f"PID {pid} is {image_name!r}, expected {process_name!r}"
        )
    return type("VerifiedProcess", (), {"pid": pid, "name": image_name})()


def load_frida() -> Any:
    try:
        import frida  # type: ignore
    except ImportError as exc:
        raise CaptureConfigurationError(
            "Frida is not installed in this Python environment. Run: "
            r"python -m pip install frida-tools"
        ) from exc
    return frida


def wait_for_modules(session: Any, module_names: list[str], timeout_seconds: float = 45) -> None:
    ready = threading.Event()
    failure: list[str] = []
    source = """
const required = %s;
function probe() {
  const loaded = new Set(Process.enumerateModules().map((item) => item.name.toLowerCase()));
  const missing = required.filter((name) => !loaded.has(name.toLowerCase()));
  if (!missing.length) { send({ready: true}); return true; }
  return false;
}
if (!probe()) { const timer = setInterval(() => { if (probe()) clearInterval(timer); }, 100); }
""" % json.dumps(module_names, separators=(",", ":"))
    probe = session.create_script(source, name="runtime-module-wait")

    def on_message(message: dict[str, Any], _data: bytes | None) -> None:
        if message.get("type") == "error":
            failure.append(str(message.get("description", message)))
            ready.set()
        elif isinstance(message.get("payload"), dict) and message["payload"].get("ready"):
            ready.set()

    probe.on("message", on_message)
    probe.load()
    try:
        if not ready.wait(timeout_seconds):
            raise RuntimeError(
                f"timed out waiting for runtime modules: {', '.join(module_names)}"
            )
        if failure:
            raise RuntimeError(f"module-wait agent failed: {failure[0]}")
    finally:
        probe.unload()


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

    previous_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, lambda _signum, _frame: stop.set())
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
                f"normal Frida attach was refused for PID {process.pid}: {exc}"
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
        signal.signal(signal.SIGINT, previous_sigint)
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


def main() -> int:
    args = parse_args()
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


if __name__ == "__main__":
    raise SystemExit(main())
