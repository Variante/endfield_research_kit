r"""Audio capture adapter for :mod:`runtime_trace`.

This is deliberately separate from the mission trace. It reuses the mission
trace launcher only for file verification, process selection, Frida loading,
and module waiting; its manifest, agent, event schema, and evidence boundary
are audio-specific.

Run from the repository root with the repo-local Frida environment::

    tools\frida-runtime\venv\Scripts\python.exe -m \
        scripts.webui.story_recovery.runtime_trace capture --profile audio

The capture is read-only. It records authored carrier calls, AudioAdapter
requests, and playing-id controls; it does not change arguments or prevent
playback.
"""
from __future__ import annotations

import argparse
import math
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from scripts.repo_paths import REPO_ROOT
from scripts.game_data.il2cpp.native_image import pe_mapped_image_size

ROOT = REPO_ROOT
SCRIPT_DIR = Path(__file__).resolve().parent

from scripts.webui.story_recovery import runtime_trace_core as core


DEFAULT_MANIFEST = SCRIPT_DIR / "audio_runtime_trace_hooks.json"
DEFAULT_AGENT = SCRIPT_DIR / "audio_runtime_trace_agent.js"
EVENT_SCHEMA = "audioRuntimeTrace.event.v1"
MANIFEST_SCHEMA = "audioRuntimeTrace.hooks.v2"
AUDIO_AGENT_PLACEHOLDER = "__AUDIO_TRACE_CONFIG__"
MAX_ABI_ARGUMENT_INDEX = 63
ABI_ARGUMENT_KINDS = frozenset({"pointer", "string", "u32", "i32", "u64", "bool", "utf16"})
ABI_RETURN_KINDS = ABI_ARGUMENT_KINDS | {"void"}


def module_wait_seconds(value: str) -> float:
    seconds = float(value)
    if not math.isfinite(seconds) or not 0 < seconds <= 900:
        raise argparse.ArgumentTypeError("module wait must be finite and greater than zero, at most 900 seconds")
    return seconds


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--game-root",
        type=Path,
        default=None,
        help="Selected game install root; omitted uses a call-time configured root.",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--agent", type=Path, default=DEFAULT_AGENT)
    parser.add_argument(
        "--process",
        help="Expected process name; omitted uses the hash-locked manifest value.",
    )
    parser.add_argument(
        "--pid",
        type=int,
        help=(
            "Attach to this already-running PID after verifying its process name. "
            "Use this when the game was started normally before the capture command."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Raw event-v1 JSONL output; omitted uses the timestamped capture path.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=900.0,
        help="Seconds to wait for the expected process when --pid is omitted (default: 900).",
    )
    parser.add_argument(
        "--duration",
        type=float,
        help="Stop the capture after this many seconds; omitted runs until Ctrl+C or detach.",
    )
    parser.add_argument(
        "--module-wait-seconds", type=module_wait_seconds, default=300.0,
        help="Seconds to wait for runtime modules after attaching, before arming (default: 300; maximum: 900).",
    )
    parser.add_argument(
        "--stop-file", type=Path,
        help="Stop cooperatively when this file appears; used by the Windows capture wrapper.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Verify files, hook ranges, manifest, and rendered agent without attaching.",
    )


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
        if "allowNull" in spec and (kind != "pointer" or type(spec["allowNull"]) is not bool):
            raise core.CaptureConfigurationError(f"{label} args[{name!r}] allowNull requires a pointer and boolean")
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
        previous_memory_kinds: dict[str, str] = {}
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
                "utf16Direct",
            }:
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] has unsupported kind"
                )
            condition = spec.get("requireMemory")
            if condition is not None:
                valid = isinstance(condition, dict)
                name = condition.get("name") if valid else None
                kind = previous_memory_kinds.get(name) if isinstance(name, str) else None
                valid = valid and (
                    (set(condition) == {"name", "equals"} and kind == "u32"
                     and type(condition["equals"]) is int and 0 <= condition["equals"] <= 0xffffffff)
                    or (set(condition) == {"name", "nonzero"} and kind == "pointer"
                        and condition["nonzero"] is True)
                )
                if not valid:
                    raise core.CaptureConfigurationError(
                        f"nativeHooks[{index}].memory[{mem_index}] requireMemory must test an earlier "
                        "u32 field for equality or an earlier pointer for nonzero"
                    )
            if "samplePhase" in spec and spec["samplePhase"] not in ("entry", "result"):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] samplePhase must be entry or result"
                )
            condition = spec.get("requireArgument")
            if condition is not None:
                valid = isinstance(condition, dict) and set(condition) == {"name", "nonzero"}
                name = condition.get("name") if valid else None
                argument = (hook.get("args") or {}).get(name) if isinstance(name, str) else None
                if not valid or condition["nonzero"] is not True or not argument or argument.get("kind") != "pointer":
                    raise core.CaptureConfigurationError(
                        f"nativeHooks[{index}].memory[{mem_index}] requireArgument must test a declared pointer for nonzero"
                    )
            previous_memory_kinds[spec["name"]] = spec.get("kind", "pointer")
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


def validated_module_base(value: Any, image_size: int, label: str) -> str:
    """Bound an ASLR image extent without reading process memory."""
    if (not isinstance(value, str) or not value.startswith("0x") or not 3 <= len(value) <= 18
            or any(character not in "0123456789abcdefABCDEF" for character in value[2:])):
        raise RuntimeError(f"{label}: expected hexadecimal module base")
    try:
        base = int(value, 16)
    except ValueError as exc:
        raise RuntimeError(f"{label}: invalid module base") from exc
    if base <= 0 or base % 4096 or not 0 < image_size < 0x800000000000 - base:
        raise RuntimeError(f"{label}: module extent is outside bounded Win64 user space")
    return hex(base)


def validate_attached_module(
    ready_payload: dict[str, Any],
    expected_module: Path,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    actual_path = ready_payload.get("modulePath")
    actual_size = ready_payload.get("moduleSize")
    expected_path = expected_module.resolve()
    expected_size = pe_mapped_image_size(expected_path)
    expected_hash = (expected_sha256 or core.sha256_file(expected_path)).casefold()
    if not isinstance(actual_path, str) or not actual_path.strip():
        raise RuntimeError("Frida agent did not report the attached GameAssembly path")
    if isinstance(actual_size, bool) or not isinstance(actual_size, int) or actual_size <= 0:
        raise RuntimeError("Frida agent did not report a valid attached GameAssembly size")
    actual_hash = _attached_file_sha256(actual_path)
    facts = {
        "expectedModulePath": str(expected_path),
        "expectedModuleSize": expected_size,
        "expectedModuleFileSize": expected_path.stat().st_size,
        "expectedModuleSha256": expected_hash,
        "attachedModulePath": actual_path,
        "attachedModuleSize": actual_size,
        "attachedModuleSha256": actual_hash,
        "modulePathMatch": core.normalized_path(actual_path) == core.normalized_path(expected_path),
        "moduleSizeMatch": actual_size == expected_size,
        "moduleSha256Match": actual_hash is not None and actual_hash == expected_hash,
        "moduleNameMatch": isinstance(ready_payload.get("moduleName"), str)
        and ready_payload["moduleName"].casefold() == expected_path.name.casefold(),
    }
    if not all(facts[key] for key in ("modulePathMatch", "moduleSizeMatch", "moduleSha256Match", "moduleNameMatch")):
        raise RuntimeError(
            "attached GameAssembly does not match the hash-verified module: "
            f"pathMatch={facts['modulePathMatch']}, sizeMatch={facts['moduleSizeMatch']}, "
            f"sha256Match={facts['moduleSha256Match']}, nameMatch={facts['moduleNameMatch']}"
        )
    facts["attachedModuleName"] = expected_path.name
    facts["attachedModuleBase"] = validated_module_base(ready_payload.get("moduleBase"), expected_size, "GameAssembly")
    return facts


def validate_attached_native_module(
    ready_payload: dict[str, Any], expected_module: Path, expected_sha256: str | None = None
) -> dict[str, Any]:
    actual_path = ready_payload.get("nativeModulePath")
    actual_size = ready_payload.get("nativeModuleSize")
    expected_path = expected_module.resolve()
    expected_size = pe_mapped_image_size(expected_path)
    expected_hash = (expected_sha256 or core.sha256_file(expected_path)).casefold()
    if not isinstance(actual_path, str) or not actual_path.strip():
        raise RuntimeError("Frida agent did not report the attached AkSoundEngine path")
    if isinstance(actual_size, bool) or not isinstance(actual_size, int) or actual_size <= 0:
        raise RuntimeError("Frida agent did not report a valid attached AkSoundEngine size")
    facts = {
        "expectedNativeModulePath": str(expected_path),
        "expectedNativeModuleSize": expected_size,
        "expectedNativeModuleFileSize": expected_path.stat().st_size,
        "expectedNativeModuleSha256": expected_hash,
        "attachedNativeModulePath": actual_path,
        "attachedNativeModuleSize": actual_size,
        "attachedNativeModuleSha256": _attached_file_sha256(actual_path),
        "nativeModulePathMatch": core.normalized_path(actual_path) == core.normalized_path(expected_path),
        "nativeModuleSizeMatch": actual_size == expected_size,
        "nativeModuleNameMatch": isinstance(ready_payload.get("nativeModuleName"), str)
        and ready_payload["nativeModuleName"].casefold() == expected_path.name.casefold(),
    }
    facts["nativeModuleSha256Match"] = (
        facts["attachedNativeModuleSha256"] is not None
        and facts["attachedNativeModuleSha256"].casefold() == expected_hash
    )
    if not all(
        facts[key]
        for key in ("nativeModulePathMatch", "nativeModuleSizeMatch", "nativeModuleSha256Match", "nativeModuleNameMatch")
    ):
        raise RuntimeError(
            "attached AkSoundEngine does not match the hash-verified module: "
            f"pathMatch={facts['nativeModulePathMatch']}, sizeMatch={facts['nativeModuleSizeMatch']}, "
            f"sha256Match={facts['nativeModuleSha256Match']}, nameMatch={facts['nativeModuleNameMatch']}"
        )
    facts["attachedNativeModuleName"] = expected_path.name
    facts["attachedNativeModuleBase"] = validated_module_base(ready_payload.get("nativeModuleBase"), expected_size, "AkSoundEngine")
    return facts


def stop_capture_agent(script: Any, writer: Any, capture_failures: list[str], delivered_diagnostics=lambda: 0) -> dict[str, Any]:
    """Check a responsive agent's captured-frame drain and delivery receipt."""
    closure = script.exports_sync.stopaudiocapture()
    expected_count = closure.get("emittedEventCount") if isinstance(closure, dict) else None
    active_count = closure.get("activeNativeCallCount") if isinstance(closure, dict) else None
    managed_count = closure.get("activeManagedCallCount") if isinstance(closure, dict) else None
    diagnostic_count = closure.get("emittedDiagnosticCount") if isinstance(closure, dict) else None
    valid_counts = all(isinstance(value, int) and not isinstance(value, bool) and value >= 0
                       for value in (expected_count, active_count, managed_count, diagnostic_count))
    drained = isinstance(closure, dict) and closure.get("stopProtocol") == "drain-v1" and closure.get("captureDrained") is True
    flush_deadline = time.monotonic() + 2
    while (valid_counts and (writer.event_count < expected_count + 1 or delivered_diagnostics() < diagnostic_count)
           and time.monotonic() < flush_deadline):
        time.sleep(0.01)
    delivered_count = writer.event_count - 1
    facts = {"captureComplete": valid_counts and drained and not capture_failures and active_count == 0
             and managed_count == 0 and delivered_count == expected_count and delivered_diagnostics() == diagnostic_count}
    protocol = closure.get("stopProtocol") if isinstance(closure, dict) else None
    facts.update(captureStopProtocol=protocol if isinstance(protocol, str) and len(protocol) <= 32 else None,
                 captureDrained=drained)
    if valid_counts:
        facts.update(agentEventCount=expected_count, activeNativeCallCount=active_count,
                     activeManagedCallCount=managed_count, droppedEventCount=max(0, expected_count - delivered_count))
        facts.update(agentDiagnosticCount=diagnostic_count, deliveredAgentDiagnosticCount=delivered_diagnostics())
    return facts


def validate_stop_file(path: Path | None, protected: list[Path]) -> Path | None:
    """A request marker must be new and distinct from evidence/native files."""
    if path is None:
        return None
    resolved = path.resolve()
    selected = core.normalized_path(str(resolved))
    for item in protected:
        if selected == core.normalized_path(str(item.resolve())):
            raise core.CaptureConfigurationError(f"--stop-file aliases protected capture/native input: {item}")
    if resolved.exists() or path.is_symlink():
        raise core.CaptureConfigurationError(f"--stop-file already exists; use a fresh request marker: {resolved}")
    return resolved


class AudioEventWriter(core.EventWriter):
    def __init__(self, output: Path, session_id: str, start: float) -> None:
        super().__init__(output, session_id, start, EVENT_SCHEMA)

    @property
    def event_count(self) -> int:
        return self.counts["event"]

    def event(self, kind: str, values: dict[str, Any] | None = None) -> None:
        self.emit(kind, values)


def validate_hook_readiness(
    manifest: dict[str, Any], ready_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Refuse arming without required hooks; native hooks default to optional."""
    hooks = ready_payload.get("hooks", {})
    native_hooks = ready_payload.get("nativeHooks", {})
    if not isinstance(hooks, dict):
        raise RuntimeError("audio hook agent returned an invalid hook status payload")
    if not isinstance(native_hooks, dict):
        raise RuntimeError("audio hook agent returned an invalid native hook status payload")
    required_managed = {
        row["name"] for row in manifest["hooks"]
        if row.get("required", row["name"] == "AudioAdapter._PostEvent")
    }
    required_native = {
        row["name"] for row in manifest.get("nativeHooks", []) if row.get("required", False)
    }
    failed = {name: hooks.get(name, "missing") for name in sorted(required_managed)
              if hooks.get(name) != "attached"}
    native_failed = {name: native_hooks.get(name, "missing") for name in sorted(required_native)
                     if native_hooks.get(name) != "attached"}
    if failed or native_failed:
        raise RuntimeError(f"required audio hooks failed to attach: managed={failed}, native={native_failed}")
    optional_failed = {name: state for name, state in sorted(hooks.items())
                       if state != "attached" and name not in required_managed}
    optional_native_failed = {
        row["name"]: native_hooks.get(row["name"], "missing")
        for row in sorted(manifest.get("nativeHooks", []), key=lambda row: row["name"])
        if row["name"] not in required_native and native_hooks.get(row["name"]) != "attached"
    }
    return optional_failed, optional_native_failed


def run_capture(
    args: argparse.Namespace,
    manifest: dict[str, Any],
    agent_source: str,
    verified: dict[str, Path],
) -> int:
    args.output = (args.output or default_output_path()).resolve()
    args.stop_file = validate_stop_file(args.stop_file, [args.manifest, args.agent, args.output,
        core.diagnostics_path(args.output), *verified.values()])
    stop = threading.Event()
    previous_sigint = core.install_stop_signal(stop)

    def cancelled() -> bool:
        return stop.is_set() or (args.stop_file is not None and args.stop_file.is_file())

    try:
        return _run_capture(args, manifest, agent_source, verified, stop, cancelled)
    finally:
        # Repeated Ctrl+C remains a stop request through detach and file close.
        core.restore_stop_signal(previous_sigint)


def _run_capture(
    args: argparse.Namespace, manifest: dict[str, Any], agent_source: str,
    verified: dict[str, Path], stop: threading.Event, cancelled: Callable[[], bool],
) -> int:
    def check_setup_stop() -> None:
        if cancelled():
            raise core.CaptureConfigurationError("audio capture stop requested during setup; no hooks armed")

    check_setup_stop()
    frida = core.load_frida()
    process_name = args.process or manifest["processName"]
    device = frida.get_local_device()
    check_setup_stop()
    process = (
        core.process_from_verified_pid(device, args.pid, process_name)
        if args.pid is not None
        else core.find_process(device, process_name, args.wait_seconds, cancelled=cancelled)
    )
    check_setup_stop()
    output = args.output
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
            "language": manifest.get("language") or None,
            "selectedGameRoot": str(args.game_root.resolve()),
            "expectedModulePath": str(verified["gameAssembly"].resolve()),
            "expectedModuleSize": pe_mapped_image_size(verified["gameAssembly"]),
            "expectedModuleFileSize": verified["gameAssembly"].stat().st_size,
            "expectedModuleSha256": manifest["files"]["gameAssembly"]["sha256"],
            "expectedNativeModulePath": str(verified["akSoundEngine"].resolve())
            if "akSoundEngine" in verified else None,
            "expectedNativeModuleSize": pe_mapped_image_size(verified["akSoundEngine"])
            if "akSoundEngine" in verified else None,
            "expectedNativeModuleFileSize": verified["akSoundEngine"].stat().st_size
            if "akSoundEngine" in verified else None,
            "expectedNativeModuleSha256": manifest["files"]["akSoundEngine"]["sha256"]
            if "akSoundEngine" in verified else None,
            "evidenceBoundary": manifest["evidenceBoundary"],
        },
    )
    ready = threading.Event()
    ready_payload: dict[str, Any] = {}
    module_facts: dict[str, Any] = {}
    capture_failures: list[str] = []
    cleanup_started = False
    callbacks_closed = False
    callback_lock = threading.RLock()
    delivered_agent_diagnostics = 0
    session = None
    script = None
    stop_attempted = False
    script_loaded = False

    def late_diagnostic(kind: str, values: dict[str, Any]) -> None:
        # A queued callback must never lose its failure because handles closed.
        # The strict audit runs only after this capture process has exited.
        with writer.diagnostics.open("a", encoding="utf-8", newline="\n") as handle:
            core.EventWriter._write(handle, {"sessionId": writer.session_id, "kind": kind,
                                            "utc": core.utc_now(), **values})

    def handle_message(message: dict[str, Any], data: bytes | None) -> None:
        nonlocal delivered_agent_diagnostics
        if callbacks_closed:
            late_diagnostic("late_agent_payload", {"message": message, "dataBytes": len(data or b"")})
            return
        if message.get("type") == "error":
            capture_failures.append("agent_error")
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
            delivered_agent_diagnostics += 1
            values = dict(payload["diagnostic"])
            kind = values.pop("kind", "audio_agent_diagnostic")
            writer.diagnostic(str(kind), values)
        elif channel == "ready" and isinstance(payload.get("ready"), dict):
            ready_payload.update(payload["ready"])
            ready.set()
        else:
            writer.diagnostic("unexpected_agent_payload", {"payload": payload})

    def on_message(message: dict[str, Any], data: bytes | None) -> None:
        with callback_lock:
            handle_message(message, data)

    def on_detached(*values: Any) -> None:
        with callback_lock:
            kind = "capture_cleanup_detached" if cleanup_started else "session_detached"
            details = {"values": [str(value) for value in values]}
            if callbacks_closed:
                late_diagnostic(kind, details)
            else:
                writer.diagnostic(kind, details)
            if not cleanup_started:
                capture_failures.append("session_detached")
                stop.set()

    try:
        check_setup_stop()
        print(f"Attaching read-only audio hooks to {process.name} (PID {process.pid})...", flush=True)
        try:
            session = device.attach(process.pid)
        except Exception as exc:
            writer.diagnostic("attach_refused", {"processName": process.name, "pid": process.pid, "error": str(exc)})
            writer.event("session_end")
            raise RuntimeError(core.describe_attach_refusal(process.name, process.pid, exc)) from exc
        session.on("detached", on_detached)
        module_names = [manifest["moduleName"]]
        if manifest.get("nativeHooks"):
            module_names.append(manifest["nativeModuleName"])
        core.wait_for_modules(session, module_names, timeout_seconds=args.module_wait_seconds, cancelled=cancelled)
        check_setup_stop()
        script = session.create_script(agent_source, name="audio-runtime-trace")
        script.on("message", on_message)
        check_setup_stop()
        script_loaded = True
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
                    "expectedModuleSize": pe_mapped_image_size(verified["gameAssembly"]),
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
                        "expectedNativeModuleSize": pe_mapped_image_size(verified["akSoundEngine"]),
                        "attachedNativeModulePath": ready_payload.get("nativeModulePath"),
                        "attachedNativeModuleSize": ready_payload.get("nativeModuleSize"),
                    },
                )
                raise
        writer.diagnostic("attached_module_verified", module_facts)
        try:
            optional_failed, optional_native_failed = validate_hook_readiness(manifest, ready_payload)
        except RuntimeError as exc:
            writer.diagnostic("required_audio_hook_failed", {"error": str(exc)})
            raise
        hooks = ready_payload.get("hooks", {})
        native_hooks = ready_payload.get("nativeHooks", {})
        if optional_native_failed:
            writer.diagnostic("optional_audio_native_hook_failed", {"hooks": optional_native_failed})
        if optional_failed:
            writer.diagnostic("optional_audio_hook_failed", {"hooks": optional_failed})
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
            if args.stop_file is not None and args.stop_file.is_file():
                break
            if deadline is not None and time.monotonic() >= deadline:
                break
        # Stop at the agent before closing the stream. The receipt counts sent
        # events; compare with delivered events, rather than assuming no loss.
        stop_attempted = True
        module_facts.update(stop_capture_agent(script, writer, capture_failures, lambda: delivered_agent_diagnostics))
        # Dispose the stopped script before sealing host facts; queued failures
        # remain durable through the callback barrier and adjacent diagnostics.
        stopped_script = script
        script = None
        stopped_script.unload()
        with callback_lock:
            module_facts["captureComplete"] &= not capture_failures
            writer.event("session_end", module_facts)
    except BaseException as exc:
        capture_failures.append("capture_failed")
        with callback_lock:
            writer.diagnostic("capture_failed", {"error": str(exc)})
        raise
    finally:
        cleanup_started = True
        # Keep repeated Ctrl+C idempotent until transport cleanup and durable
        # streams are closed; restoring the default earlier can interrupt them.
        try:
            if script is not None:
                stopped_script = script
                script = None
                try:
                    if script_loaded and not stop_attempted:
                        stop_attempted = True
                        try:
                            facts = stop_capture_agent(stopped_script, writer, capture_failures,
                                                       lambda: delivered_agent_diagnostics)
                        except Exception as exc:
                            capture_failures.append("capture_failure_stop_failed")
                            with callback_lock:
                                writer.diagnostic("capture_failure_stop_failed", {"error": str(exc)})
                        else:
                            with callback_lock:
                                writer.diagnostic("capture_failure_stop_receipt", facts)
                finally:
                    try:
                        stopped_script.unload()
                    except Exception as exc:
                        capture_failures.append("capture_script_unload_failed")
                        with callback_lock:
                            writer.diagnostic("capture_script_unload_failed", {"error": str(exc)})
        finally:
            try:
                if session is not None:
                    try:
                        session.detach()
                    except Exception as exc:
                        capture_failures.append("capture_session_detach_failed")
                        with callback_lock:
                            writer.diagnostic("capture_session_detach_failed", {"error": str(exc)})
            finally:
                with callback_lock:
                    writer.close()
                    callbacks_closed = True
    print(
        f"Capture stopped: {writer.event_count} audio events, "
        f"{writer.diagnostic_count} diagnostics -> {output}",
        flush=True,
    )
    return 0 if module_facts.get("captureComplete") is True and not capture_failures else 1


def capture(args: argparse.Namespace) -> int:
    try:
        selected_game_root = (
            args.game_root
            if args.game_root is not None
            else core.resolve_installed_game_data_root().parent
        ).resolve()
        args.game_root = selected_game_root
        args.output = (args.output or default_output_path()).resolve()
        manifest = load_manifest(args.manifest.resolve())
        verified = core.verify_game_files(selected_game_root, manifest)
        args.stop_file = validate_stop_file(args.stop_file, [args.manifest, args.agent, args.output,
            core.diagnostics_path(args.output), *verified.values()])
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
    except (core.CaptureConfigurationError, TimeoutError, RuntimeError, KeyError, OSError) as exc:
        print(f"Audio runtime capture failed: {exc}", file=sys.stderr)
        return 1
