"""Capture a bounded, read-only Burst resolver API trace from the retail client.

The probe reuses the shared runtime-trace process, hash gate, EventWriter, and
Frida loading infrastructure used by ``character_dynamics_telemetry.py``.
It observes ``kernel32!LoadLibraryW``, ``kernel32!GetProcAddress``, and the
returns from six pinned ``BurstDirectCall.GetFunctionPointer`` wrappers and
the two CalcLine route gates. It
never calls a returned pointer or changes game state.

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
import hashlib
import json
import re
import struct
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
EVENT_SCHEMA = "burstResolverTelemetry.event.v2"
MANIFEST_SCHEMA = "burstResolverTelemetry.hooks.v2"
AGENT_PLACEHOLDER = "__BURST_RESOLVER_TRACE_CONFIG__"
DEFAULT_OUTPUT_ROOT = ROOT / "scratch/reverse_engineering/burst_resolver_telemetry"
TARGET_IDS = {
    "start_simulation_step_range_kernel",
    "update_step_basic_poture_range_kernel",
    "end_simulation_step_range_kernel",
    "collider_start_simulation_step_range_kernel",
    "collider_end_simulation_step_range_kernel",
    "calc_line_normal_tangent_kernel",
}
TARGETS_SHA256 = "5439b71925c147bc92074cad03719b35464c6205913b6e2f916a616f2b887ada"
ROUTE_PROBES_SHA256 = "3a6bb06fc1b62974334c3fb43f9a728f6d37467b00065722680d352e29f11a75"
TARGET_WINDOW_ROLES = {
    "constructor",
    "static_constructor",
    "initializer",
    "get_function_pointer_discard",
    "get_function_pointer",
    "invoke",
}

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


def verify_call_target_probes(gameassembly: Path, manifest: dict[str, Any]) -> None:
    """Verify each observed wrapper body and indirect-call encoding in the pinned PE."""

    with gameassembly.open("rb") as stream:
        dos = stream.read(64)
        if len(dos) != 64 or dos[:2] != b"MZ":
            raise CaptureConfigurationError("GameAssembly.dll is not a PE image")
        pe_offset = struct.unpack_from("<I", dos, 0x3C)[0]
        stream.seek(pe_offset)
        header = stream.read(24)
        if len(header) != 24 or header[:4] != b"PE\0\0":
            raise CaptureConfigurationError("GameAssembly.dll has no PE signature")
        section_count = struct.unpack_from("<H", header, 6)[0]
        optional_size = struct.unpack_from("<H", header, 20)[0]
        stream.seek(pe_offset + 24 + optional_size)
        sections = []
        for _ in range(section_count):
            section = stream.read(40)
            if len(section) != 40:
                raise CaptureConfigurationError("GameAssembly.dll section table is truncated")
            virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from("<IIII", section, 8)
            sections.append((virtual_address, max(virtual_size, raw_size), raw_offset, raw_size))

        def bytes_at_rva(rva: int, size: int) -> bytes:
            for virtual_address, mapped_size, raw_offset, raw_size in sections:
                relative = rva - virtual_address
                if 0 <= relative and relative + size <= mapped_size and relative + size <= raw_size:
                    stream.seek(raw_offset + relative)
                    value = stream.read(size)
                    if len(value) == size:
                        return value
            raise CaptureConfigurationError(
                f"GameAssembly.dll RVA 0x{rva:x}+0x{size:x} is outside backed PE sections"
            )

        for target in manifest["targets"]:
            probe = target["callTargetProbe"]
            start = int(probe["invokeStartOffset"], 16)
            end = int(probe["invokeEndOffsetExclusive"], 16)
            body = bytes_at_rva(start, end - start)
            actual_hash = hashlib.sha256(body).hexdigest()
            if actual_hash != probe["invokeBodySha256"]:
                raise CaptureConfigurationError(
                    f"target {target['id']} invoke body hash drifted: {actual_hash}"
                )
            call_relative = int(probe["indirectCallOffset"], 16) - start
            expected_instruction = bytes.fromhex(probe["instructionBytes"])
            if body[call_relative:call_relative + len(expected_instruction)] != expected_instruction:
                raise CaptureConfigurationError(
                    f"target {target['id']} indirect-call instruction bytes drifted"
                )

        route_probes = manifest["routeProbes"]

        def verify_body(probe: dict[str, Any], label: str) -> None:
            start = int(probe["startOffset"], 16)
            end = int(probe["endOffsetExclusive"], 16)
            actual = hashlib.sha256(bytes_at_rva(start, end - start)).hexdigest()
            if actual != probe["bodySha256"]:
                raise CaptureConfigurationError(
                    f"route probe {label} body hash drifted: {actual}"
                )

        def verify_direct_call(
            offset_text: str,
            return_text: str,
            instruction_text: str,
            target_rva: int,
            label: str,
        ) -> None:
            offset = int(offset_text, 16)
            return_offset = int(return_text, 16)
            instruction = bytes.fromhex(instruction_text)
            if return_offset != offset + len(instruction):
                raise CaptureConfigurationError(
                    f"route probe {label} return offset drifted"
                )
            actual = bytes_at_rva(offset, len(instruction))
            if actual != instruction:
                raise CaptureConfigurationError(
                    f"route probe {label} call instruction bytes drifted"
                )
            if len(actual) != 5 or actual[0] != 0xE8:
                raise CaptureConfigurationError(
                    f"route probe {label} is not a pinned rel32 call"
                )
            displacement = struct.unpack_from("<i", actual, 1)[0]
            if return_offset + displacement != target_rva:
                raise CaptureConfigurationError(
                    f"route probe {label} direct-call target drifted"
                )

        burst = route_probes["calcLineBurstEnabled"]
        verify_body(burst, "calcLineBurstEnabled")
        verify_direct_call(
            burst["invokeCallOffset"],
            burst["invokeReturnOffset"],
            burst["callInstructionBytes"],
            int(burst["startOffset"], 16),
            "calcLineBurstEnabled",
        )
        ifix = route_probes["fromToRotationIfix"]
        verify_body(ifix, "fromToRotationIfix")
        verify_direct_call(
            ifix["callOffset"],
            ifix["callReturnOffset"],
            ifix["callInstructionBytes"],
            int(ifix["startOffset"], 16),
            "fromToRotationIfix",
        )
        for index, caller in enumerate(ifix["calcLineCallerReturns"]):
            verify_direct_call(
                caller["callOffset"],
                caller["returnOffset"],
                caller["instructionBytes"],
                int(ifix["fromToRotationStartOffset"], 16),
                f"fromToRotationIfix.calcLineCallerReturns[{index}]",
            )


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
    if not isinstance(files, dict) or set(files) != {"executable", "gameAssembly", "metadata", "resolver"}:
        raise CaptureConfigurationError(
            "manifest files must contain exactly executable, gameAssembly, metadata, and resolver"
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
    if capture.get("includeAllModuleBacktrace") is not True:
        raise CaptureConfigurationError("capture must include the bounded all-module caller backtrace")
    if not isinstance(capture.get("requireResolverExportEnumeration"), bool):
        raise CaptureConfigurationError("capture requireResolverExportEnumeration must be boolean")

    targets = manifest.get("targets")
    if not isinstance(targets, list) or len(targets) != len(TARGET_IDS) or {target.get("id") for target in targets if isinstance(target, dict)} != TARGET_IDS:
        raise CaptureConfigurationError("manifest targets must contain exactly the six pinned Burst range targets")
    target_digest = hashlib.sha256(
        json.dumps(targets, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if target_digest != TARGETS_SHA256:
        raise CaptureConfigurationError(
            f"manifest pinned Burst target windows drifted: {target_digest}"
        )
    for target in targets:
        if not isinstance(target, dict):
            raise CaptureConfigurationError("each manifest target must be an object")
        target_id = target.get("id")
        if not isinstance(target_id, str) or target_id not in TARGET_IDS:
            raise CaptureConfigurationError(f"invalid Burst target id: {target_id!r}")
        if isinstance(target.get("methodIndex"), bool) or not isinstance(target.get("methodIndex"), int) or target["methodIndex"] <= 0:
            raise CaptureConfigurationError(f"target {target_id} methodIndex is invalid")
        for key in ("methodName", "fullName"):
            if not isinstance(target.get(key), str) or not target[key].strip():
                raise CaptureConfigurationError(f"target {target_id} {key} is invalid")
        probe = target.get("callTargetProbe")
        expected_probe_keys = {
            "getFunctionPointerMethodIndex", "getFunctionPointerOffset",
            "invokeMethodIndex", "invokeStartOffset", "invokeEndOffsetExclusive",
            "invokeBodySha256", "indirectCallOffset", "targetRegister",
            "instructionBytes",
        }
        if not isinstance(probe, dict) or set(probe) != expected_probe_keys:
            raise CaptureConfigurationError(f"target {target_id} callTargetProbe is incomplete")
        for key in ("getFunctionPointerMethodIndex", "invokeMethodIndex"):
            if isinstance(probe[key], bool) or not isinstance(probe[key], int) or probe[key] <= 0:
                raise CaptureConfigurationError(f"target {target_id} callTargetProbe {key} is invalid")
        for key in (
            "getFunctionPointerOffset", "invokeStartOffset",
            "invokeEndOffsetExclusive", "indirectCallOffset",
        ):
            if not isinstance(probe[key], str) or not re.fullmatch(r"0x[0-9a-fA-F]+", probe[key]):
                raise CaptureConfigurationError(f"target {target_id} callTargetProbe {key} is invalid")
        if not isinstance(probe["invokeBodySha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", probe["invokeBodySha256"]):
            raise CaptureConfigurationError(f"target {target_id} callTargetProbe invokeBodySha256 is invalid")
        if probe["targetRegister"] not in {"rax", "rdx", "r10"}:
            raise CaptureConfigurationError(f"target {target_id} callTargetProbe targetRegister is invalid")
        if not isinstance(probe["instructionBytes"], str) or not re.fullmatch(r"[0-9a-f]{4,6}", probe["instructionBytes"]):
            raise CaptureConfigurationError(f"target {target_id} callTargetProbe instructionBytes is invalid")
        windows = target.get("windows")
        if not isinstance(windows, list) or {window.get("role") for window in windows if isinstance(window, dict)} != TARGET_WINDOW_ROLES:
            raise CaptureConfigurationError(f"target {target_id} must contain exactly the pinned wrapper/initializer windows")
        roles: set[str] = set()
        for window in windows:
            if not isinstance(window, dict):
                raise CaptureConfigurationError(f"target {target_id} window must be an object")
            role = window.get("role")
            if not isinstance(role, str) or role in roles or role not in TARGET_WINDOW_ROLES:
                raise CaptureConfigurationError(f"target {target_id} window role is invalid: {role!r}")
            roles.add(role)
            if isinstance(window.get("methodIndex"), bool) or not isinstance(window.get("methodIndex"), int) or window["methodIndex"] <= 0:
                raise CaptureConfigurationError(f"target {target_id} {role} methodIndex is invalid")
            for key in ("startOffset", "endOffsetExclusive"):
                value = window.get(key)
                if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]+", value):
                    raise CaptureConfigurationError(f"target {target_id} {role} {key} is invalid")
            if int(window["startOffset"], 16) >= int(window["endOffsetExclusive"], 16):
                raise CaptureConfigurationError(f"target {target_id} {role} window is empty or inverted")
        by_role = {window["role"]: window for window in windows}
        get_pointer = by_role["get_function_pointer"]
        invoke = by_role["invoke"]
        if (
            probe["getFunctionPointerMethodIndex"] != get_pointer["methodIndex"]
            or probe["getFunctionPointerOffset"] != get_pointer["startOffset"]
        ):
            raise CaptureConfigurationError(f"target {target_id} callTargetProbe GetFunctionPointer drifted from its window")
        if (
            probe["invokeMethodIndex"] != invoke["methodIndex"]
            or probe["invokeStartOffset"] != invoke["startOffset"]
            or probe["invokeEndOffsetExclusive"] != invoke["endOffsetExclusive"]
        ):
            raise CaptureConfigurationError(f"target {target_id} callTargetProbe invoke body drifted from its window")
        call_offset = int(probe["indirectCallOffset"], 16)
        if not int(probe["invokeStartOffset"], 16) <= call_offset < int(probe["invokeEndOffsetExclusive"], 16):
            raise CaptureConfigurationError(f"target {target_id} callTargetProbe indirect call is outside invoke body")
    route_probes = manifest.get("routeProbes")
    if not isinstance(route_probes, dict) or set(route_probes) != {
        "calcLineBurstEnabled", "fromToRotationIfix"
    }:
        raise CaptureConfigurationError("manifest routeProbes must contain the two pinned CalcLine route gates")
    route_digest = hashlib.sha256(
        json.dumps(route_probes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if route_digest != ROUTE_PROBES_SHA256:
        raise CaptureConfigurationError(
            f"manifest pinned CalcLine route probes drifted: {route_digest}"
        )
    boundary = manifest.get("evidenceBoundary")
    if not isinstance(boundary, dict) or not isinstance(boundary.get("nonClaims"), list) or not boundary["nonClaims"]:
        raise CaptureConfigurationError("manifest evidenceBoundary.nonClaims must be non-empty")
    export_enum = manifest.get("resolverExportEnumeration")
    if not isinstance(export_enum, dict) or set(export_enum) != {"hashedCount", "canonicalNameRvaSha256"}:
        raise CaptureConfigurationError("manifest resolverExportEnumeration is incomplete")
    if export_enum["hashedCount"] != 628 or not isinstance(export_enum["canonicalNameRvaSha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", export_enum["canonicalNameRvaSha256"]):
        raise CaptureConfigurationError("manifest resolverExportEnumeration is not hash-pinned")
    return manifest


def render_agent_source(
    path: Path,
    manifest: dict[str, Any],
    resolver_expected_path: Path | None = None,
) -> str:
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
            "targets": manifest["targets"],
            "routeProbes": manifest["routeProbes"],
            "resolverExpectedPath": str(resolver_expected_path.resolve()) if resolver_expected_path else None,
            "resolverExpectedSize": manifest["files"]["resolver"]["bytes"],
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


def validate_resolver_handshake(
    ready_payload: dict[str, Any],
    expected_resolver: Path,
    expected_size: int,
    expected_export_enumeration: dict[str, Any],
) -> None:
    """Fail closed when an already-loaded resolver is not the pinned file."""

    identity = ready_payload.get("resolverModuleIdentity")
    if not isinstance(identity, dict) or identity.get("base") is None:
        return
    actual_path = identity.get("path")
    actual_size = identity.get("size")
    actual_name = identity.get("name")
    actual_base = identity.get("base")
    actual_module_base = identity.get("moduleBase")
    if not isinstance(actual_name, str) or actual_name.casefold() != expected_resolver.name.casefold():
        raise RuntimeError("agent reported an unexpected already-loaded resolver module name")
    if not isinstance(actual_path, str) or not actual_path.strip():
        raise RuntimeError("agent did not report the already-loaded resolver module path")
    if (
        not isinstance(actual_base, str)
        or not re.fullmatch(r"0x[0-9a-fA-F]+", actual_base)
        or actual_base.casefold() in {"0x0", "0x0000000000000000"}
        or actual_module_base != actual_base
    ):
        raise RuntimeError("agent did not report a valid already-loaded resolver module base")
    if core.normalized_path(actual_path) != core.normalized_path(expected_resolver):
        raise RuntimeError(
            "attached resolver module does not match the hash-verified resolver: "
            f"expected={expected_resolver}, got={actual_path}"
        )
    if isinstance(actual_size, bool) or not isinstance(actual_size, int) or actual_size != expected_size:
        raise RuntimeError(
            "attached resolver module size does not match the hash-verified resolver: "
            f"expected={expected_size}, got={actual_size}"
        )
    entries = ready_payload.get("resolverExportMap")
    if not isinstance(entries, list) or len(entries) != expected_export_enumeration["hashedCount"]:
        raise RuntimeError("agent did not report the complete hash-pinned resolver export map")
    canonical: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"name", "offset"}:
            raise RuntimeError("agent reported a malformed resolver export map entry")
        name = entry["name"]
        offset = entry["offset"]
        if not isinstance(name, str) or not re.fullmatch(r"[0-9a-f]{32}", name):
            raise RuntimeError("agent reported a non-hashed resolver export")
        if not isinstance(offset, str) or not re.fullmatch(r"0x[0-9a-fA-F]+", offset):
            raise RuntimeError("agent reported an invalid resolver export offset")
        canonical.append(f"{name}:{int(offset, 16):x}")
    digest = hashlib.sha256(("\n".join(sorted(canonical)) + "\n").encode()).hexdigest()
    if digest != expected_export_enumeration["canonicalNameRvaSha256"]:
        raise RuntimeError("runtime resolver export name/RVA map differs from the pinned manifest")


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
        validate_resolver_handshake(
            ready_payload,
            verified["resolver"],
            manifest["files"]["resolver"]["bytes"],
            manifest["resolverExportEnumeration"],
        )
        if ready_payload.get("kernel32ModuleName", "").casefold() != manifest["kernel32ModuleName"].casefold():
            raise RuntimeError("agent did not confirm the expected kernel32 module")
        if ready_payload.get("resolverModuleName", "").casefold() != manifest["resolverModuleName"].casefold():
            raise RuntimeError("agent did not confirm the expected Burst resolver module name")
        hooks = ready_payload.get("hooks")
        call_target_hooks = ready_payload.get("callTargetHooks")
        route_probe_hooks = ready_payload.get("routeProbeHooks")
        failed = ready_payload.get("failed") or []
        if not isinstance(hooks, dict) or set(hooks) != set(manifest["hooks"]):
            raise RuntimeError(f"agent hook handshake is incomplete: {hooks}")
        if failed or any(value != "attached" for value in hooks.values()):
            raise RuntimeError(f"one or more Burst resolver hooks failed to attach: {failed or hooks}")
        if not isinstance(call_target_hooks, dict) or set(call_target_hooks) != TARGET_IDS:
            raise RuntimeError(f"agent call-target hook handshake is incomplete: {call_target_hooks}")
        if any(value != "attached" for value in call_target_hooks.values()):
            raise RuntimeError(f"one or more Burst call-target hooks failed to attach: {call_target_hooks}")
        if not isinstance(route_probe_hooks, dict) or set(route_probe_hooks) != set(manifest["routeProbes"]):
            raise RuntimeError(f"agent CalcLine route-probe handshake is incomplete: {route_probe_hooks}")
        if any(value != "attached" for value in route_probe_hooks.values()):
            raise RuntimeError(f"one or more CalcLine route-probe hooks failed to attach: {route_probe_hooks}")
        writer.emit(
            "native_module_verified",
            {
                **module_facts,
                "verifiedFiles": file_facts,
                "hookStates": hooks,
                "callTargetHookStates": call_target_hooks,
                "routeProbeHookStates": route_probe_hooks,
                "kernel32ModuleName": ready_payload["kernel32ModuleName"],
                "resolverModuleName": ready_payload["resolverModuleName"],
                "resolverModuleIdentity": ready_payload.get("resolverModuleIdentity"),
                "resolverExpectedPath": str(verified["resolver"].resolve()),
                "resolverExpectedSize": manifest["files"]["resolver"]["bytes"],
                "resolverExportMapSha256": manifest["resolverExportEnumeration"]["canonicalNameRvaSha256"],
                "resolverExportMapCount": manifest["resolverExportEnumeration"]["hashedCount"],
                "gameAssemblyModuleName": ready_payload.get("moduleName"),
                "gameAssemblyModuleBase": ready_payload.get("moduleBase"),
                "gameAssemblyModuleSize": ready_payload.get("moduleSize"),
                "targets": ready_payload.get("targets"),
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
        verify_call_target_probes(verified["gameAssembly"], manifest)
        agent_source = render_agent_source(
            args.agent.resolve(), manifest, verified["resolver"]
        )
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
