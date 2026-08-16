"""Capture the current-build GameplayTag name/id registry from a running client.

Run from the repository root with the repo-local Frida environment::

    tools\\frida-runtime\\venv\\Scripts\\python.exe -m \\
        scripts.gameplay_builder.capture_runtime_tags

The capture is read-only.  It verifies the exact executable, GameAssembly, and
global-metadata pair before attaching, then records only tag method observations
and the config-set build boundary.  The output JSONL is intentionally separate
from generated WebUI data until it is validated and passed to the Gameplay
builder.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..story_recovery import runtime_trace_core as core


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_GAME_ROOT = core.DEFAULT_GAME_ROOT
DEFAULT_MANIFEST = SCRIPT_DIR / "gameplay_tag_runtime_hooks.json"
DEFAULT_AGENT = SCRIPT_DIR / "gameplay_tag_runtime_agent.js"
MANIFEST_SCHEMA = "gameplayTagRuntimeTrace.hooks.v1"
EVENT_SCHEMA = "gameplayTagRuntimeTrace.event.v1"
AGENT_PLACEHOLDER = "__GAMEPLAY_TAG_TRACE_CONFIG__"


def default_output_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "scratch" / "reverse_engineering" / "gameplay_tag_runtime" / f"capture-{stamp}.jsonl"


def load_manifest(path: Path) -> dict[str, Any]:
    value = core.load_manifest_object(path, MANIFEST_SCHEMA, "GameplayTag runtime hook")
    for key in ("gameBuild", "processName", "moduleName"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise core.CaptureConfigurationError(f"manifest {key} must be a non-empty string")
    files = value.get("files")
    if not isinstance(files, dict) or not files:
        raise core.CaptureConfigurationError("manifest files must be a non-empty object")
    for required in ("executable", "gameAssembly", "metadata"):
        if required not in files:
            raise core.CaptureConfigurationError(f"manifest is missing files.{required}")
    hooks = value.get("hooks")
    if not isinstance(hooks, list) or not hooks:
        raise core.CaptureConfigurationError("manifest hooks must be a non-empty list")
    names: set[str] = set()
    for index, hook in enumerate(hooks):
        if not isinstance(hook, dict):
            raise core.CaptureConfigurationError(f"hooks[{index}] must be an object")
        name = hook.get("name")
        if not isinstance(name, str) or not name.strip() or name in names:
            raise core.CaptureConfigurationError(f"hooks[{index}] has a duplicate/invalid name")
        names.add(name)
        if hook.get("kind") not in {"request", "name", "lookup", "build"}:
            raise core.CaptureConfigurationError(f"hooks[{index}] has an invalid kind")
        rva = hook.get("rva")
        if not isinstance(rva, str) or not rva.lower().startswith("0x"):
            raise core.CaptureConfigurationError(f"hooks[{index}] has an invalid RVA")
        try:
            if int(rva, 16) <= 0:
                raise ValueError
        except ValueError as exc:
            raise core.CaptureConfigurationError(f"hooks[{index}] has an invalid RVA: {rva!r}") from exc
        if not isinstance(hook.get("sourceKind"), str) or not hook["sourceKind"].strip():
            raise core.CaptureConfigurationError(f"hooks[{index}] sourceKind is required")
        if "required" in hook and not isinstance(hook["required"], bool):
            raise core.CaptureConfigurationError(f"hooks[{index}] required must be boolean")
    if not isinstance(value.get("evidenceBoundary"), dict):
        raise core.CaptureConfigurationError("manifest evidenceBoundary must be an object")
    return value


def render_agent_source(path: Path, manifest: dict[str, Any]) -> str:
    return core.render_agent_template(
        path,
        AGENT_PLACEHOLDER,
        {
            "gameBuild": manifest["gameBuild"],
            "moduleName": manifest["moduleName"],
            "hooks": manifest["hooks"],
            "evidenceBoundary": manifest["evidenceBoundary"],
        },
        "GameplayTag",
    )


def validate_hook_ranges(manifest: dict[str, Any], game_assembly: Path) -> None:
    module_size = game_assembly.stat().st_size
    invalid = []
    for hook in manifest["hooks"]:
        rva = int(hook["rva"], 16)
        if rva >= module_size:
            invalid.append(f"{hook['name']}={hook['rva']}")
    if invalid:
        raise core.CaptureConfigurationError(
            "GameplayTag hook RVA is outside the verified GameAssembly range: "
            + ", ".join(invalid)
        )


class TagEventWriter(core.EventWriter):
    def __init__(self, output: Path, session_id: str, start: float) -> None:
        super().__init__(output, session_id, start, EVENT_SCHEMA)

    def event(self, kind: str, values: dict[str, Any] | None = None) -> None:
        self.emit(kind, values)


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


def capture(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest.resolve())
    game_root = args.game_root.resolve()
    verified = core.verify_game_files(game_root, manifest)
    validate_hook_ranges(manifest, verified["gameAssembly"])
    agent_source = render_agent_source(args.agent.resolve(), manifest)
    if args.check_only:
        print(
            f"GameplayTag hooks verified for {manifest['gameBuild']}: "
            f"{len(manifest['hooks'])} hooks; no process attached."
        )
        return 0

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
    writer = TagEventWriter(output, session_id, start)
    writer.event(
        "session_start",
        {
            "gameBuild": manifest["gameBuild"],
            "captureTool": f"frida-gameplay-tag-runtime/{getattr(frida, '__version__', 'unknown')}",
            "expectedModulePath": str(verified["gameAssembly"].resolve()),
            "expectedModuleSize": verified["gameAssembly"].stat().st_size,
            "gameAssemblySha256": manifest["files"]["gameAssembly"]["sha256"],
            "metadataSha256": manifest["files"]["metadata"]["sha256"],
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
            kind = values.pop("kind", "gameplay_tag_agent_diagnostic")
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
        print(f"Attaching read-only GameplayTag hooks to {process.name} (PID {process.pid})...", flush=True)
        try:
            session = device.attach(process.pid)
        except Exception as exc:
            writer.diagnostic(
                "attach_refused",
                {
                    "processName": process.name,
                    "pid": process.pid,
                    "error": str(exc),
                },
            )
            writer.event("session_end")
            raise RuntimeError(
                f"normal Frida attach was refused for PID {process.pid}: {exc}"
            ) from exc
        session.on("detached", on_detached)
        core.wait_for_modules(session, [manifest["moduleName"]])
        script = session.create_script(agent_source, name="gameplay-tag-runtime")
        script.on("message", on_message)
        script.load()
        if not ready.wait(15):
            raise RuntimeError("GameplayTag hook agent did not report ready within 15 seconds")
        module_facts = core.validate_attached_module(ready_payload, verified["gameAssembly"])
        writer.diagnostic("attached_module_verified", module_facts)
        hooks = ready_payload.get("hooks", {})
        required = {
            hook["name"] for hook in manifest["hooks"] if hook.get("required", True)
        }
        failed = {name: hooks.get(name, "missing") for name in sorted(required) if hooks.get(name) != "attached"}
        if failed:
            raise RuntimeError(f"one or more GameplayTag hooks failed to attach: {failed}")
        print(
            f"Capture armed: {sum(state == 'attached' for state in hooks.values())}/{len(hooks)} hooks.\n"
            f"Output: {output}\nDiagnostics: {writer.diagnostics}\n"
            "Start or load scenes that initialize gameplay tags, then press Ctrl+C to stop.",
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
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    args = parser.parse_args(argv)
    try:
        return capture(args)
    except (core.CaptureConfigurationError, TimeoutError, RuntimeError, OSError) as exc:
        print(f"GameplayTag runtime capture failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
