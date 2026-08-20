r"""Audio capture adapter for :mod:`runtime_trace`.

This is deliberately separate from the mission trace. It reuses the mission
trace launcher only for file verification, process selection, Frida loading,
and module waiting; its manifest, agent, event schema, and evidence boundary
are audio-specific.

Run from the repository root with the repo-local Frida environment::

    tools\frida-runtime\venv\Scripts\python.exe -m \
        scripts.story_recovery.runtime_trace capture --profile audio

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

from . import runtime_trace_core as core


DEFAULT_MANIFEST = SCRIPT_DIR / "audio_runtime_trace_hooks.json"
DEFAULT_AGENT = SCRIPT_DIR / "audio_runtime_trace_agent.js"
EVENT_SCHEMA = "audioRuntimeTrace.event.v1"
MANIFEST_SCHEMA = "audioRuntimeTrace.hooks.v2"
AUDIO_AGENT_PLACEHOLDER = "__AUDIO_TRACE_CONFIG__"
MAX_ABI_ARGUMENT_INDEX = 63
ABI_ARGUMENT_KINDS = frozenset({"pointer", "string", "u32", "i32", "u64", "bool", "utf16"})
ABI_RETURN_KINDS = ABI_ARGUMENT_KINDS | {"void"}


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--game-root",
        type=Path,
        default=None,
        help="Selected game install root; omitted uses a call-time configured root.",
    )
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


def _validate_abi_contract(hook: dict[str, Any], label: str) -> None:
    args = hook.get("args")
    if args is not None and not isinstance(args, dict):
        raise core.CaptureConfigurationError(f"{label} args must be an object")
    for name, spec in (args or {}).items():
        if not isinstance(name, str) or not name.strip() or not isinstance(spec, dict):
            raise core.CaptureConfigurationError(f"{label} args[{name!r}] must be an object")
        index = spec.get("index")
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or index < 0
            or index > MAX_ABI_ARGUMENT_INDEX
        ):
            raise core.CaptureConfigurationError(
                f"{label} args[{name!r}] index must be in 0..{MAX_ABI_ARGUMENT_INDEX}"
            )
        kind = spec.get("kind", "pointer")
        if not isinstance(kind, str) or kind not in ABI_ARGUMENT_KINDS:
            raise core.CaptureConfigurationError(f"{label} args[{name!r}] has unsupported kind")
    string_args = hook.get("stringArgs")
    if string_args is not None and not isinstance(string_args, dict):
        raise core.CaptureConfigurationError(f"{label} stringArgs must be an object")
    for raw_index, name in (string_args or {}).items():
        try:
            index = int(raw_index)
        except (TypeError, ValueError) as exc:
            raise core.CaptureConfigurationError(
                f"{label} stringArgs index must be an integer"
            ) from exc
        if (
            isinstance(raw_index, bool)
            or index < 0
            or index > MAX_ABI_ARGUMENT_INDEX
            or str(index) != str(raw_index)
            or not isinstance(name, str)
            or not name.strip()
        ):
            raise core.CaptureConfigurationError(
                f"{label} stringArgs index must be in 0..{MAX_ABI_ARGUMENT_INDEX} "
                "and name a field"
            )
    return_kind = hook.get("returnKind", "void")
    if not isinstance(return_kind, str) or return_kind not in ABI_RETURN_KINDS:
        raise core.CaptureConfigurationError(f"{label} has unsupported returnKind")


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
    native_module_name = value.get("nativeModuleName")
    native_hooks = value.get("nativeHooks", [])
    if native_module_name is not None and (
        not isinstance(native_module_name, str) or not native_module_name.strip()
    ):
        raise core.CaptureConfigurationError("manifest nativeModuleName must be a non-empty string")
    if not isinstance(native_hooks, list):
        raise core.CaptureConfigurationError("audio manifest nativeHooks must be a list")
    if native_hooks and "akSoundEngine" not in files:
        raise core.CaptureConfigurationError(
            "audio manifest nativeHooks require files.akSoundEngine"
        )
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
        _validate_abi_contract(hook, f"hooks[{index}]")
        stack_arguments = hook.get("stackArguments")
        if stack_arguments is not None and not isinstance(stack_arguments, list):
            raise core.CaptureConfigurationError(
                f"hooks[{index}] stackArguments must be a list"
            )
        for stack_index, spec in enumerate(stack_arguments or []):
            if (
                not isinstance(spec, dict)
                or not isinstance(spec.get("name"), str)
                or not spec["name"].strip()
            ):
                raise core.CaptureConfigurationError(
                    f"hooks[{index}].stackArguments[{stack_index}] must name a field"
                )
            offset = spec.get("offset")
            if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
                raise core.CaptureConfigurationError(
                    f"hooks[{index}].stackArguments[{stack_index}] offset must be non-negative"
                )
            if not isinstance(spec.get("kind", "pointer"), str) or spec.get("kind", "pointer") not in {
                "pointer", "u32", "i32", "u64", "utf16",
            }:
                raise core.CaptureConfigurationError(
                    f"hooks[{index}].stackArguments[{stack_index}] has unsupported kind"
                )
    native_names: set[str] = set()
    for index, hook in enumerate(native_hooks):
        if not isinstance(hook, dict):
            raise core.CaptureConfigurationError(f"nativeHooks[{index}] must be an object")
        name = hook.get("name")
        if not isinstance(name, str) or not name.strip() or name in native_names:
            raise core.CaptureConfigurationError(f"nativeHooks[{index}] has a duplicate/invalid name")
        native_names.add(name)
        rva = hook.get("rva")
        if not isinstance(rva, str) or not rva.lower().startswith("0x"):
            raise core.CaptureConfigurationError(f"nativeHooks[{index}] has an invalid RVA")
        try:
            if int(rva, 16) < 0:
                raise ValueError
        except ValueError as exc:
            raise core.CaptureConfigurationError(
                f"nativeHooks[{index}] has an invalid RVA: {rva!r}"
            ) from exc
        if not isinstance(hook.get("sourceKind"), str) or not hook["sourceKind"].strip():
            raise core.CaptureConfigurationError(f"nativeHooks[{index}] sourceKind is required")
        if "required" in hook and not isinstance(hook["required"], bool):
            raise core.CaptureConfigurationError(f"nativeHooks[{index}] required must be boolean")
        _validate_abi_contract(hook, f"nativeHooks[{index}]")
        memory = hook.get("memory")
        if memory is not None and not isinstance(memory, list):
            raise core.CaptureConfigurationError(f"nativeHooks[{index}] memory must be a list")
        for mem_index, spec in enumerate(memory or []):
            if (
                not isinstance(spec, dict)
                or not isinstance(spec.get("name"), str)
                or not spec["name"].strip()
            ):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] must name a field"
                )
            if "argIndex" in spec and (
                isinstance(spec["argIndex"], bool)
                or not isinstance(spec["argIndex"], int)
                or not 0 <= spec["argIndex"] <= MAX_ABI_ARGUMENT_INDEX
            ):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] argIndex must be in "
                    f"0..{MAX_ABI_ARGUMENT_INDEX}"
                )
            has_arg_index = (
                isinstance(spec.get("argIndex"), int)
                and not isinstance(spec["argIndex"], bool)
                and spec["argIndex"] <= MAX_ABI_ARGUMENT_INDEX
                and spec["argIndex"] >= 0
            )
            has_stack_offset = (
                isinstance(spec.get("stackOffset"), int)
                and not isinstance(spec["stackOffset"], bool)
                and spec["stackOffset"] >= 0
            )
            has_base_field = isinstance(spec.get("baseField"), str) and bool(
                spec["baseField"].strip()
            )
            if sum((has_arg_index, has_stack_offset, has_base_field)) != 1:
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] needs exactly one non-negative "
                    "argIndex, stackOffset, or baseField"
                )
            if "savePointer" in spec and not isinstance(spec["savePointer"], bool):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] savePointer must be boolean"
                )
            pointer_offsets = spec.get("pointerOffsets")
            if pointer_offsets is not None and (
                not isinstance(pointer_offsets, list)
                or any(
                    not isinstance(item, int)
                    or isinstance(item, bool)
                    or item < 0
                    for item in pointer_offsets
                )
            ):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] pointerOffsets must be "
                    "a list of non-negative integers"
                )
            if "pointerOffset" in spec and "pointerOffsets" in spec:
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] cannot set both "
                    "pointerOffset and pointerOffsets"
                )
            if "pointerOffset" in spec and (
                not isinstance(spec["pointerOffset"], int)
                or isinstance(spec["pointerOffset"], bool)
                or spec["pointerOffset"] < 0
            ):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] pointerOffset must be non-negative"
                )
            if (
                not isinstance(spec.get("offset", 0), int)
                or isinstance(spec.get("offset", 0), bool)
                or spec.get("offset", 0) < 0
            ):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] offset must be non-negative"
                )
            if not isinstance(spec.get("kind", "pointer"), str) or spec.get("kind", "pointer") not in {
                "pointer",
                "u32",
                "i32",
                "u64",
                "utf16",
            }:
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] has unsupported kind"
                )
    if native_hooks and not native_module_name:
        raise core.CaptureConfigurationError("nativeHooks require nativeModuleName")
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
            "nativeModuleName": manifest.get("nativeModuleName"),
            "nativeHooks": manifest.get("nativeHooks", []),
            "evidenceBoundary": manifest["evidenceBoundary"],
        },
        "audio",
    )


def validate_hook_ranges(
    manifest: dict[str, Any],
    game_assembly: Path,
    native_module: Path | None = None,
) -> None:
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

    native_hooks = manifest.get("nativeHooks", [])
    if not native_hooks:
        return
    if native_module is None:
        raise core.CaptureConfigurationError(
            "native hook range validation requires the verified AkSoundEngine module"
        )
    try:
        native_size = native_module.stat().st_size
    except OSError as exc:
        raise core.CaptureConfigurationError(
            f"cannot stat AkSoundEngine for audio hook range validation: {native_module}"
        ) from exc
    invalid_native = []
    for hook in native_hooks:
        rva = int(hook["rva"], 16)
        if rva <= 0 or rva >= native_size:
            invalid_native.append(f"{hook['name']}={hook['rva']}")
    if invalid_native:
        raise core.CaptureConfigurationError(
            "audio native hook RVA is outside the verified AkSoundEngine range "
            f"(0x0..0x{native_size - 1:x}): {', '.join(invalid_native)}"
        )


def _attached_file_sha256(path_text: str) -> str | None:
    try:
        path = Path(path_text).resolve()
        return core.sha256_file(path) if path.is_file() else None
    except OSError:
        return None


def validate_attached_module(
    ready_payload: dict[str, Any],
    expected_module: Path,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    actual_path = ready_payload.get("modulePath")
    actual_size = ready_payload.get("moduleSize")
    expected_path = expected_module.resolve()
    expected_size = expected_path.stat().st_size
    expected_hash = (expected_sha256 or core.sha256_file(expected_path)).casefold()
    if not isinstance(actual_path, str) or not actual_path.strip():
        raise RuntimeError("Frida agent did not report the attached GameAssembly path")
    if isinstance(actual_size, bool) or not isinstance(actual_size, int) or actual_size <= 0:
        raise RuntimeError("Frida agent did not report a valid attached GameAssembly size")
    actual_hash = _attached_file_sha256(actual_path)
    facts = {
        "expectedModulePath": str(expected_path),
        "expectedModuleSize": expected_size,
        "expectedModuleSha256": expected_hash,
        "attachedModulePath": actual_path,
        "attachedModuleSize": actual_size,
        "attachedModuleSha256": actual_hash,
        "modulePathMatch": core.normalized_path(actual_path) == core.normalized_path(expected_path),
        "moduleSizeMatch": actual_size == expected_size,
        "moduleSha256Match": actual_hash is not None and actual_hash == expected_hash,
    }
    if not all(facts[key] for key in ("modulePathMatch", "moduleSizeMatch", "moduleSha256Match")):
        raise RuntimeError(
            "attached GameAssembly does not match the hash-verified module: "
            f"pathMatch={facts['modulePathMatch']}, sizeMatch={facts['moduleSizeMatch']}, "
            f"sha256Match={facts['moduleSha256Match']}"
        )
    return facts


def validate_attached_native_module(
    ready_payload: dict[str, Any], expected_module: Path, expected_sha256: str | None = None
) -> dict[str, Any]:
    actual_path = ready_payload.get("nativeModulePath")
    actual_size = ready_payload.get("nativeModuleSize")
    expected_path = expected_module.resolve()
    expected_size = expected_path.stat().st_size
    expected_hash = (expected_sha256 or core.sha256_file(expected_path)).casefold()
    if not isinstance(actual_path, str) or not actual_path.strip():
        raise RuntimeError("Frida agent did not report the attached AkSoundEngine path")
    if isinstance(actual_size, bool) or not isinstance(actual_size, int) or actual_size <= 0:
        raise RuntimeError("Frida agent did not report a valid attached AkSoundEngine size")
    facts = {
        "expectedNativeModulePath": str(expected_path),
        "expectedNativeModuleSize": expected_size,
        "expectedNativeModuleSha256": expected_hash,
        "attachedNativeModulePath": actual_path,
        "attachedNativeModuleSize": actual_size,
        "attachedNativeModuleSha256": _attached_file_sha256(actual_path),
        "nativeModulePathMatch": core.normalized_path(actual_path) == core.normalized_path(expected_path),
        "nativeModuleSizeMatch": actual_size == expected_size,
    }
    facts["nativeModuleSha256Match"] = (
        facts["attachedNativeModuleSha256"] is not None
        and facts["attachedNativeModuleSha256"].casefold() == expected_hash
    )
    if not all(
        facts[key]
        for key in ("nativeModulePathMatch", "nativeModuleSizeMatch", "nativeModuleSha256Match")
    ):
        raise RuntimeError(
            "attached AkSoundEngine does not match the hash-verified module: "
            f"pathMatch={facts['nativeModulePathMatch']}, sizeMatch={facts['nativeModuleSizeMatch']}, "
            f"sha256Match={facts['nativeModuleSha256Match']}"
        )
    return facts


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
            "selectedGameRoot": str(args.game_root.resolve()),
            "expectedModulePath": str(verified["gameAssembly"].resolve()),
            "expectedModuleSize": verified["gameAssembly"].stat().st_size,
            "expectedModuleSha256": manifest["files"]["gameAssembly"]["sha256"],
            "expectedNativeModulePath": str(verified["akSoundEngine"].resolve())
            if "akSoundEngine" in verified else None,
            "expectedNativeModuleSize": verified["akSoundEngine"].stat().st_size
            if "akSoundEngine" in verified else None,
            "expectedNativeModuleSha256": manifest["files"]["akSoundEngine"]["sha256"]
            if "akSoundEngine" in verified else None,
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
        module_names = [manifest["moduleName"]]
        if manifest.get("nativeHooks"):
            module_names.append(manifest["nativeModuleName"])
        core.wait_for_modules(session, module_names)
        script = session.create_script(agent_source, name="audio-runtime-trace")
        script.on("message", on_message)
        script.load()
        if not ready.wait(15):
            raise RuntimeError("audio hook agent did not report ready within 15 seconds")
        try:
            module_facts = validate_attached_module(
                ready_payload,
                verified["gameAssembly"],
                manifest["files"]["gameAssembly"]["sha256"],
            )
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
        if manifest.get("nativeHooks"):
            try:
                module_facts.update(
                    validate_attached_native_module(
                        ready_payload,
                        verified["akSoundEngine"],
                        manifest["files"]["akSoundEngine"]["sha256"],
                    )
                )
            except RuntimeError as exc:
                writer.diagnostic(
                    "attached_native_module_mismatch",
                    {
                        "error": str(exc),
                        "expectedNativeModulePath": str(verified["akSoundEngine"].resolve()),
                        "expectedNativeModuleSize": verified["akSoundEngine"].stat().st_size,
                        "attachedNativeModulePath": ready_payload.get("nativeModulePath"),
                        "attachedNativeModuleSize": ready_payload.get("nativeModuleSize"),
                    },
                )
                raise
        writer.diagnostic("attached_module_verified", module_facts)
        hooks = ready_payload.get("hooks", {})
        if not isinstance(hooks, dict):
            raise RuntimeError("audio hook agent returned an invalid hook status payload")
        native_hooks = ready_payload.get("nativeHooks", {})
        if not isinstance(native_hooks, dict):
            raise RuntimeError("audio hook agent returned an invalid native hook status payload")
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
        native_failed = {
            name: native_hooks.get(name, "missing")
            for name in (hook["name"] for hook in manifest.get("nativeHooks", []))
            if native_hooks.get(name) != "attached"
        }
        if native_failed:
            writer.diagnostic("optional_audio_native_hook_failed", {"hooks": native_failed})
        if optional_failed:
            writer.diagnostic("optional_audio_hook_failed", {"hooks": optional_failed})
        if failed:
            raise RuntimeError(f"one or more audio hooks failed to attach: {failed}")
        attached_count = sum(state == "attached" for state in hooks.values())
        native_attached_count = sum(state == "attached" for state in native_hooks.values())
        optional_failure_text = (
            f"Optional hook failures: {optional_failed}\n" if optional_failed else ""
        )
        print(
            f"Capture armed: {attached_count}/{len(hooks)} managed + "
            f"{native_attached_count}/{len(native_hooks)} native audio hooks attached.\n"
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
        selected_game_root = (
            args.game_root
            if args.game_root is not None
            else core.resolve_installed_game_data_root().parent
        ).resolve()
        args.game_root = selected_game_root
        manifest = load_manifest(args.manifest.resolve())
        verified = core.verify_game_files(selected_game_root, manifest)
        validate_hook_ranges(
            manifest,
            verified["gameAssembly"],
            verified.get("akSoundEngine"),
        )
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
