"""Fail-closed validator for Burst resolver telemetry JSONL captures."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import burst_resolver_telemetry as telemetry  # noqa: E402


SCHEMA = telemetry.EVENT_SCHEMA
BASE_EVENT_KEYS = {"schema", "sessionId", "seq", "monotonicMs", "utc", "kind"}


class TraceValidationError(ValueError):
    pass


def _fail(message: str) -> None:
    raise TraceValidationError(message)


def _strict_event_keys(row: dict[str, Any], kind: str, extra: set[str]) -> None:
    expected = BASE_EVENT_KEYS | extra
    if set(row) != expected:
        if kind == "get_proc_address" and "callerBacktrace" in expected - set(row):
            _fail(f"{kind} caller backtrace schema is not exact: expected {sorted(expected)}, got {sorted(row)}")
        _fail(f"{kind} event schema is not exact: expected {sorted(expected)}, got {sorted(row)}")


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


def _verified_files(start: dict[str, Any], manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    facts = start.get("verifiedFiles")
    if not isinstance(facts, dict) or set(facts) != set(manifest["files"]):
        _fail("session_start verifiedFiles must contain exactly the three pinned native files")
    for name, expected in manifest["files"].items():
        actual = facts.get(name)
        if not isinstance(actual, dict):
            _fail(f"session_start missing verified file fact {name}")
        if actual.get("bytes") != expected["bytes"]:
            _fail(f"session_start verified file fact drift for {name} bytes")
        if str(actual.get("sha256", "")).casefold() != expected["sha256"].casefold():
            _fail(f"session_start verified file fact drift for {name} sha256")
        if not isinstance(actual.get("path"), str) or not actual["path"]:
            _fail(f"session_start verified file fact {name} has no path")
    return facts


def _check_pointer(value: Any, label: str, *, allow_null: bool = False) -> None:
    if allow_null and value is None:
        return
    if not isinstance(value, str) or not value:
        _fail(f"{label} must be a non-empty pointer string")
    if not re.fullmatch(r"0x[0-9a-fA-F]+", value):
        _fail(f"{label} is not a pointer string")
    if not allow_null and value.lower() in {"0x0", "0x0000000000000000"}:
        _fail(f"{label} must not be null")


def _module_name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{label} must be a non-empty module name")
    return value.casefold()


def _module_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{label} must be a non-empty module path")
    return value.replace("/", "\\").casefold()


def _target_windows(manifest: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for target in manifest["targets"]:
        result[target["id"]] = {window["role"]: window for window in target["windows"]}
    return result


def _frame(
    value: Any,
    label: str,
    *,
    expected_module: str | None = None,
    expected_path: str | None = None,
    expected_size: int | None = None,
    expected_base: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} is not an object")
    required = {"address", "module", "modulePath", "moduleBase", "moduleSize", "offset"}
    if set(value) != required:
        _fail(f"{label} has an unexpected frame schema: {sorted(value)}")
    _check_pointer(value.get("address"), f"{label}.address")
    module = _module_name(value.get("module"), f"{label}.module")
    path = _module_path(value.get("modulePath"), f"{label}.modulePath")
    _check_pointer(value.get("moduleBase"), f"{label}.moduleBase")
    size = value.get("moduleSize")
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        _fail(f"{label}.moduleSize is invalid")
    _check_pointer(value.get("offset"), f"{label}.offset")
    if expected_module is not None and module != expected_module.casefold():
        _fail(f"{label} contains a non-GameAssembly frame")
    if expected_path is not None and path != expected_path:
        _fail(f"{label} belongs to a different module path")
    if expected_size is not None and size != expected_size:
        _fail(f"{label} module size drifted")
    base = int(value["moduleBase"], 16)
    offset = int(value["offset"], 16)
    address = int(value["address"], 16)
    if offset >= size:
        _fail(f"{label} offset lies outside its module image")
    if address != base + offset:
        _fail(f"{label} address is not moduleBase plus offset")
    if expected_base is not None and base != int(expected_base, 16):
        _fail(f"{label} module base differs from the native handshake")
    return value


def _module_identity(value: Any, label: str, manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} is not an object")
    required = {"status", "name", "path", "base", "moduleBase", "size", "exportEnumerationStatus", "hashedExportCount"}
    if set(value) != required:
        _fail(f"{label} has an unexpected module identity schema: {sorted(value)}")
    status = value.get("status")
    if status not in {"already_loaded", "loadlibraryw", "not_loaded_at_attach"}:
        _fail(f"{label}.status is invalid or unrecognized")
    if _module_name(value.get("name"), f"{label}.name") != manifest["resolverModuleName"].casefold():
        _fail(f"{label}.name differs from the pinned resolver")
    if status == "not_loaded_at_attach":
        if any(value.get(key) is not None for key in ("path", "base", "moduleBase", "size")):
            _fail(f"{label} not_loaded identity must have null path/base/size")
        if value.get("exportEnumerationStatus") != "not_loaded" or value.get("hashedExportCount") != 0:
            _fail(f"{label} not_loaded identity has inconsistent export enumeration fields")
    else:
        _module_path(value.get("path"), f"{label}.path")
        _check_pointer(value.get("base"), f"{label}.base")
        _check_pointer(value.get("moduleBase"), f"{label}.moduleBase")
        if value["base"].casefold() != value["moduleBase"].casefold():
            _fail(f"{label}.base and moduleBase differ")
    size = value.get("size")
    if status == "not_loaded_at_attach":
        if size is not None:
            _fail(f"{label}.size must be null before module load")
    elif isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        _fail(f"{label}.size is invalid")
    if value.get("exportEnumerationStatus") not in {"available", "unavailable", "not_loaded", "not_enumerated", "null_return"}:
        _fail(f"{label}.exportEnumerationStatus is invalid")
    count = value.get("hashedExportCount")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        _fail(f"{label}.hashedExportCount is invalid")
    return value


def _pinned_resolver_identity(
    value: Any,
    label: str,
    manifest: dict[str, Any],
    expected_path: str,
) -> dict[str, Any]:
    identity = _module_identity(value, label, manifest)
    if identity.get("status") != "not_loaded_at_attach":
        if _module_path(identity.get("path"), f"{label}.path") != expected_path:
            _fail(f"{label}.path differs from the pinned resolver")
        if identity.get("size") != manifest["files"]["resolver"]["bytes"]:
            _fail(f"{label}.size differs from the pinned resolver")
    return identity


def _resolved_fields(row: dict[str, Any], label: str) -> None:
    required = {
        "resolvedAddress", "resolvedModuleName", "resolvedModulePath", "resolvedModuleBase",
        "resolvedModuleSize", "resolvedModuleOffset", "resolvedExportName", "resolvedExportStatus",
    }
    if not required.issubset(row):
        _fail(f"{label} is missing resolved pointer fields")
    status = row.get("resolvedExportStatus")
    if status not in {"null_return", "enumerated", "not_enumerated", "unavailable", "not_loaded"}:
        _fail(f"{label}.resolvedExportStatus is invalid")
    address = row.get("resolvedAddress")
    return_pointer = row.get("returnPointer")
    if address is None:
        if return_pointer not in {None, "0x0", "0x0000000000000000"}:
            _fail(f"{label} resolvedAddress is null for a non-null return")
        for key in ("resolvedModuleName", "resolvedModulePath", "resolvedModuleBase", "resolvedModuleSize", "resolvedModuleOffset", "resolvedExportName"):
            if row.get(key) is not None:
                _fail(f"{label}.{key} must be null when GetProcAddress returned NULL")
        if status != "null_return":
            _fail(f"{label} null return has the wrong resolvedExportStatus")
        return
    _check_pointer(address, f"{label}.resolvedAddress")
    _check_pointer(return_pointer, f"{label}.returnPointer")
    if address.casefold() != return_pointer.casefold():
        _fail(f"{label}.resolvedAddress differs from returnPointer")
    _module_name(row.get("resolvedModuleName"), f"{label}.resolvedModuleName")
    _module_path(row.get("resolvedModulePath"), f"{label}.resolvedModulePath")
    _check_pointer(row.get("resolvedModuleBase"), f"{label}.resolvedModuleBase")
    size = row.get("resolvedModuleSize")
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        _fail(f"{label}.resolvedModuleSize is invalid")
    _check_pointer(row.get("resolvedModuleOffset"), f"{label}.resolvedModuleOffset")
    if row.get("resolvedExportName") is not None and (
        not isinstance(row["resolvedExportName"], str) or not row["resolvedExportName"]
    ):
        _fail(f"{label}.resolvedExportName is invalid")
    export_name = row.get("resolvedExportName")
    if status == "enumerated" and not isinstance(export_name, str):
        _fail(f"{label}.enumerated result must include resolvedExportName")
    if status != "enumerated" and export_name is not None:
        _fail(f"{label}.{status} result must not include resolvedExportName")
    resolved_base = int(row["resolvedModuleBase"], 16)
    resolved_offset = int(row["resolvedModuleOffset"], 16)
    resolved_address = int(row["resolvedAddress"], 16)
    if resolved_offset >= size:
        _fail(f"{label}.resolvedModuleOffset lies outside its module image")
    if resolved_address != resolved_base + resolved_offset:
        _fail(f"{label}.resolvedAddress is not resolvedModuleBase plus resolvedModuleOffset")


def _cpu_selection(
    value: Any,
    label: str,
    manifest: dict[str, Any],
    expected_resolver_path: str,
    expected_resolver_base: str | None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} is not an object")
    required = {
        "probe", "status", "slotAddress", "selectedPointer",
        "resolvedAddress", "resolvedModuleName", "resolvedModulePath",
        "resolvedModuleBase", "resolvedModuleSize", "resolvedModuleOffset",
        "selectedCpuVariant", "error",
    }
    if set(value) != required:
        _fail(f"{label} has an unexpected CPU selection schema: {sorted(value)}")
    status = value.get("status")
    if status not in {
        "not_configured", "resolver_unavailable", "slot_unreadable",
        "slot_null", "unknown_entry", "matched",
    }:
        _fail(f"{label}.status is invalid")
    nullable_resolution = (
        "resolvedAddress", "resolvedModuleName", "resolvedModulePath",
        "resolvedModuleBase", "resolvedModuleSize", "resolvedModuleOffset",
    )
    if status == "not_configured":
        if value.get("probe") is not None:
            _fail(f"{label}.probe must be null when not configured")
        for key in (
            "slotAddress", "selectedPointer", *nullable_resolution,
            "selectedCpuVariant", "error",
        ):
            if value.get(key) is not None:
                _fail(f"{label}.{key} must be null when not configured")
        return value

    probe = manifest["calcLineCpuSelection"]
    if value.get("probe") != probe:
        _fail(f"{label}.probe drifted from the pinned CalcLine CPU selection")
    if status == "resolver_unavailable":
        for key in (
            "slotAddress", "selectedPointer", *nullable_resolution,
            "selectedCpuVariant", "error",
        ):
            if value.get(key) is not None:
                _fail(f"{label}.{key} must be null when the resolver is unavailable")
        return value

    slot_address = value.get("slotAddress")
    _check_pointer(slot_address, f"{label}.slotAddress")
    if expected_resolver_base is not None:
        expected_slot = int(expected_resolver_base, 16) + int(
            probe["functionPointerSlotRva"], 16
        )
        if int(slot_address, 16) != expected_slot:
            _fail(f"{label}.slotAddress is not the pinned resolver slot")

    if status == "slot_unreadable":
        if not isinstance(value.get("error"), str) or not value["error"]:
            _fail(f"{label}.error must explain an unreadable slot")
        for key in ("selectedPointer", *nullable_resolution, "selectedCpuVariant"):
            if value.get(key) is not None:
                _fail(f"{label}.{key} must be null when the slot is unreadable")
        return value
    if value.get("error") is not None:
        _fail(f"{label}.error is only valid for an unreadable slot")

    selected_pointer = value.get("selectedPointer")
    _check_pointer(selected_pointer, f"{label}.selectedPointer", allow_null=True)
    if status == "slot_null":
        if selected_pointer not in {"0x0", "0x0000000000000000"}:
            _fail(f"{label}.selectedPointer must be null for slot_null")
        for key in (*nullable_resolution, "selectedCpuVariant"):
            if value.get(key) is not None:
                _fail(f"{label}.{key} must be null for slot_null")
        return value
    _check_pointer(selected_pointer, f"{label}.selectedPointer")
    resolved_address = value.get("resolvedAddress")
    _check_pointer(resolved_address, f"{label}.resolvedAddress")
    if resolved_address.casefold() != selected_pointer.casefold():
        _fail(f"{label}.resolvedAddress differs from selectedPointer")

    module_fields = (
        value.get("resolvedModuleName"), value.get("resolvedModulePath"),
        value.get("resolvedModuleBase"), value.get("resolvedModuleSize"),
        value.get("resolvedModuleOffset"),
    )
    if any(field is not None for field in module_fields):
        if any(field is None for field in module_fields):
            _fail(f"{label} has a partial selected-entry module identity")
        _module_name(value["resolvedModuleName"], f"{label}.resolvedModuleName")
        _module_path(value["resolvedModulePath"], f"{label}.resolvedModulePath")
        _check_pointer(value["resolvedModuleBase"], f"{label}.resolvedModuleBase")
        size = value["resolvedModuleSize"]
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            _fail(f"{label}.resolvedModuleSize is invalid")
        _check_pointer(value["resolvedModuleOffset"], f"{label}.resolvedModuleOffset")
        if int(value["resolvedModuleOffset"], 16) >= size:
            _fail(f"{label}.resolvedModuleOffset lies outside its module image")
        if int(resolved_address, 16) != (
            int(value["resolvedModuleBase"], 16) +
            int(value["resolvedModuleOffset"], 16)
        ):
            _fail(f"{label}.resolvedAddress is not module base plus offset")

    if status == "unknown_entry":
        if value.get("selectedCpuVariant") is not None:
            _fail(f"{label}.selectedCpuVariant must be null for an unknown entry")
        return value

    if status != "matched":
        _fail(f"{label}.status is inconsistent with a non-null selected entry")
    if _module_name(value.get("resolvedModuleName"), f"{label}.resolvedModuleName") != manifest["resolverModuleName"].casefold():
        _fail(f"{label} matched entry is outside the pinned resolver")
    if _module_path(value.get("resolvedModulePath"), f"{label}.resolvedModulePath") != expected_resolver_path:
        _fail(f"{label} matched entry belongs to a different resolver path")
    if value.get("resolvedModuleSize") != manifest["files"]["resolver"]["bytes"]:
        _fail(f"{label} matched entry has the wrong resolver size")
    if expected_resolver_base is not None and str(value.get("resolvedModuleBase")).casefold() != expected_resolver_base.casefold():
        _fail(f"{label} matched entry has the wrong resolver base")
    variants = {
        variant["cpuVariant"]: variant["entryRva"]
        for variant in probe["variants"]
    }
    cpu_variant = value.get("selectedCpuVariant")
    if cpu_variant not in variants:
        _fail(f"{label}.selectedCpuVariant is not a pinned variant")
    if int(value["resolvedModuleOffset"], 16) != int(variants[cpu_variant], 16):
        _fail(f"{label}.selectedCpuVariant does not match the selected entry RVA")
    return value


def validate_trace(
    path: Path,
    manifest_path: Path = telemetry.DEFAULT_MANIFEST,
) -> dict[str, Any]:
    manifest = telemetry.load_manifest(manifest_path.resolve())
    rows = load_rows(path.resolve())
    session_values = [row.get("sessionId") for row in rows]
    if any(not isinstance(value, str) or not value for value in session_values):
        _fail("trace rows must have a non-empty string sessionId")
    if len(set(session_values)) != 1:
        _fail("trace must contain exactly one non-empty sessionId")
    expected_seq = 0
    strict_success_fields = {
        "session_start": {
            "gameBuild", "captureTool", "exportFingerprint", "verifiedFiles",
            "kernel32ModuleName", "resolverModuleName", "nativeEvidenceBoundary",
        },
        "native_module_verified": {
            "expectedModulePath", "expectedModuleSize", "attachedModulePath", "attachedModuleSize",
            "modulePathMatch", "moduleSizeMatch", "verifiedFiles", "hookStates", "callTargetHookStates",
            "routeProbeHookStates",
            "kernel32ModuleName", "resolverModuleName", "resolverModuleIdentity",
            "resolverExpectedPath", "resolverExpectedSize", "gameAssemblyModuleName",
            "gameAssemblyModuleBase", "gameAssemblyModuleSize", "targets",
            "resolverExportMapSha256", "resolverExportMapCount",
        },
        "resolver_module_loaded": {
            "requestedPath", "hModule", "loadSucceeded", "module", "resolverModuleIdentity",
            "resolverExportMap", "resolverExportMapCount",
        },
        "capture_started": {"trigger"},
        "get_proc_address": {
            "requestOrdinal", "hModule", "lpProcName", "lpProcNameType", "requestedExportIsHashed",
            "returnPointer", "resolverModule", "resolvedAddress", "resolvedModuleName",
            "resolvedModulePath", "resolvedModuleBase", "resolvedModuleSize", "resolvedModuleOffset",
            "resolvedExportName", "resolvedExportStatus", "caller", "callerBacktrace",
            "callerBacktraceStatus", "gameAssemblyCallerBacktrace", "backtraceStatus",
            "targetWindowMatches", "targetAttributionStatus", "targetAttributionTargets", "threadId",
        },
        "burst_function_pointer": {
            "targetId", "targetMethodIndex", "targetMethodName", "targetFullName",
            "callTargetProbe", "returnPointer", "resolvedAddress", "resolvedModuleName",
            "resolvedModulePath", "resolvedModuleBase", "resolvedModuleSize",
            "resolvedModuleOffset", "resolvedExportName", "resolvedExportStatus",
            "cpuSelection", "threadId",
        },
        "calc_line_burst_gate": {
            "probe", "methodIndex", "methodName", "result", "returnRegister",
            "callerReturnOffset", "methodInfo", "threadId",
        },
        "calc_line_ifix_gate": {
            "probe", "methodIndex", "methodName", "result", "patchId",
            "returnRegister", "fromToReturnOffset", "calcLineRoute",
            "calcLineCallerReturnOffset", "methodInfo", "threadId",
        },
        "capture_stop_ack": {"eventCount", "captureStarted", "terminalState", "resolverModuleIdentity"},
        "session_end": {"captureStarted", "stopAck", "terminalFailure"},
    }
    for index, row in enumerate(rows):
        if row.get("schema") != SCHEMA:
            _fail(f"row {index} has unexpected schema {row.get('schema')!r}")
        if row.get("seq") != expected_seq:
            _fail(f"row {index} sequence is {row.get('seq')!r}, expected {expected_seq}")
        expected_seq += 1
        if not isinstance(row.get("kind"), str) or not row["kind"]:
            _fail(f"row {index} has no event kind")
        if row["kind"] in strict_success_fields:
            _strict_event_keys(row, row["kind"], strict_success_fields[row["kind"]])

    expected_phase = ["session_start", "native_module_verified", "capture_started"]
    if len(rows) < len(expected_phase) + 2:
        _fail("trace is too short to contain the canonical capture phases")
    if [row.get("kind") for row in rows[:3]] != expected_phase:
        _fail("trace event order must begin session_start -> native_module_verified -> capture_started")
    if rows[-2].get("kind") != "capture_stop_ack" or rows[-1].get("kind") != "session_end":
        _fail("trace event order must end capture_stop_ack -> session_end")
    middle_kinds = [row.get("kind") for row in rows[3:-2]]
    if any(kind not in {
        "resolver_module_loaded", "get_proc_address", "burst_function_pointer",
        "calc_line_burst_gate", "calc_line_ifix_gate",
    } for kind in middle_kinds):
        _fail("resolver/proc/call-target events are only valid between capture_started and capture_stop_ack")

    starts = [row for row in rows if row.get("kind") == "session_start"]
    ends = [row for row in rows if row.get("kind") == "session_end"]
    handshakes = [row for row in rows if row.get("kind") == "native_module_verified"]
    if len(starts) != 1 or len(ends) != 1 or len(handshakes) != 1:
        _fail(
            "expected exactly one session_start/native_module_verified/session_end, got "
            f"{len(starts)}/{len(handshakes)}/{len(ends)}"
        )
    start = starts[0]
    if start.get("gameBuild") != manifest["gameBuild"]:
        _fail("session gameBuild differs from the pinned manifest")
    if start.get("exportFingerprint") != manifest["files"]["metadata"]["sha256"]:
        _fail("session metadata fingerprint differs from the pinned manifest")
    if _module_name(start.get("kernel32ModuleName"), "session kernel32ModuleName") != manifest["kernel32ModuleName"].casefold():
        _fail("session kernel32 module differs from the pinned manifest")
    if _module_name(start.get("resolverModuleName"), "session resolverModuleName") != manifest["resolverModuleName"].casefold():
        _fail("session resolver module differs from the pinned manifest")
    file_facts = _verified_files(start, manifest)

    handshake = handshakes[0]
    for key in ("modulePathMatch", "moduleSizeMatch"):
        if handshake.get(key) is not True:
            _fail(f"native module handshake did not validate {key}")
    if handshake.get("verifiedFiles") != file_facts:
        _fail("native module handshake file facts differ from session_start")
    attached_module_path = _module_path(
        handshake.get("attachedModulePath"), "native module handshake attachedModulePath"
    )
    attached_module_size = handshake.get("attachedModuleSize")
    if isinstance(attached_module_size, bool) or not isinstance(attached_module_size, int) or attached_module_size <= 0:
        _fail("native module handshake attachedModuleSize is invalid")
    if _module_name(handshake.get("gameAssemblyModuleName"), "handshake gameAssemblyModuleName") != manifest["moduleName"].casefold():
        _fail("native module handshake GameAssembly name drifted")
    _check_pointer(handshake.get("gameAssemblyModuleBase"), "native module handshake gameAssemblyModuleBase")
    gameassembly_module_base = handshake["gameAssemblyModuleBase"]
    gameassembly_module_size = handshake.get("gameAssemblyModuleSize")
    if isinstance(gameassembly_module_size, bool) or not isinstance(gameassembly_module_size, int) or gameassembly_module_size <= 0:
        _fail("native module handshake gameAssemblyModuleSize is invalid")
    if gameassembly_module_size != attached_module_size:
        _fail("native module handshake GameAssembly size differs from attachedModuleSize")
    if _module_name(handshake.get("kernel32ModuleName"), "handshake kernel32ModuleName") != manifest["kernel32ModuleName"].casefold():
        _fail("native module handshake kernel32 name drifted")
    if _module_name(handshake.get("resolverModuleName"), "handshake resolverModuleName") != manifest["resolverModuleName"].casefold():
        _fail("native module handshake resolver module name drifted")
    hook_states = handshake.get("hookStates")
    if not isinstance(hook_states, dict) or set(hook_states) != set(manifest["hooks"]):
        _fail("native module handshake does not list both resolver hooks")
    if any(value != "attached" for value in hook_states.values()):
        _fail("native module handshake does not prove every resolver hook attached")
    call_target_hook_states = handshake.get("callTargetHookStates")
    if not isinstance(call_target_hook_states, dict) or set(call_target_hook_states) != telemetry.TARGET_IDS:
        _fail("native module handshake does not list all six call-target hooks")
    if any(value != "attached" for value in call_target_hook_states.values()):
        _fail("native module handshake does not prove every call-target hook attached")
    route_probe_hook_states = handshake.get("routeProbeHookStates")
    if not isinstance(route_probe_hook_states, dict) or set(route_probe_hook_states) != set(manifest["routeProbes"]):
        _fail("native module handshake does not list both CalcLine route probes")
    if any(value != "attached" for value in route_probe_hook_states.values()):
        _fail("native module handshake does not prove every CalcLine route probe attached")
    resolver_identity = handshake.get("resolverModuleIdentity")
    if not isinstance(resolver_identity, dict):
        _fail("native module handshake has no resolver module identity")
    _module_identity(resolver_identity, "resolver module identity", manifest)
    identity_handle = resolver_identity.get("base")
    if identity_handle is not None:
        _check_pointer(identity_handle, "resolver module identity base")
    expected_resolver_path = _module_path(file_facts["resolver"]["path"], "pinned resolver path")
    handshake_expected_path = _module_path(
        handshake.get("resolverExpectedPath"), "native module handshake resolverExpectedPath"
    )
    if handshake_expected_path != expected_resolver_path:
        _fail("native module handshake resolverExpectedPath differs from the pinned file")
    if handshake.get("resolverExpectedSize") != manifest["files"]["resolver"]["bytes"]:
        _fail("native module handshake resolverExpectedSize differs from the pinned file")
    export_enum = manifest["resolverExportEnumeration"]
    if handshake.get("resolverExportMapSha256") != export_enum["canonicalNameRvaSha256"] or handshake.get("resolverExportMapCount") != export_enum["hashedCount"]:
        _fail("native module handshake resolver export map is not the pinned name/RVA map")
    handshake_targets = handshake.get("targets")
    if not isinstance(handshake_targets, list) or len(handshake_targets) != len(manifest["targets"]):
        _fail("native module handshake target list is incomplete")
    expected_targets = {
        target["id"]: {
            "id": target["id"],
            "methodIndex": target["methodIndex"],
            "methodName": target["methodName"],
            "windowCount": len(target["windows"]),
        }
        for target in manifest["targets"]
    }
    actual_targets: dict[str, dict[str, Any]] = {}
    for target in handshake_targets:
        if not isinstance(target, dict) or set(target) != {"id", "methodIndex", "methodName", "windowCount"}:
            _fail("native module handshake target entry schema is invalid")
        target_id = target.get("id")
        if target_id in actual_targets or target_id not in expected_targets:
            _fail("native module handshake target id is duplicated or unknown")
        if target != expected_targets[target_id]:
            _fail(f"native module handshake target {target_id!r} drifted")
        actual_targets[target_id] = target
    if resolver_identity.get("status") != "not_loaded_at_attach":
        if _module_path(resolver_identity.get("path"), "resolver module identity path") != expected_resolver_path:
            _fail("resolver module identity path differs from the pinned file")
        if resolver_identity.get("size") != manifest["files"]["resolver"]["bytes"]:
            _fail("resolver module identity size differs from the pinned file")

    resolver_events = [row for row in rows if row.get("kind") == "resolver_module_loaded"]
    proc_events = [row for row in rows if row.get("kind") == "get_proc_address"]
    pointer_events = [row for row in rows if row.get("kind") == "burst_function_pointer"]
    burst_gate_events = [row for row in rows if row.get("kind") == "calc_line_burst_gate"]
    ifix_gate_events = [row for row in rows if row.get("kind") == "calc_line_ifix_gate"]
    observed_handles: set[str] = set()
    if isinstance(identity_handle, str) and identity_handle:
        observed_handles.add(identity_handle.casefold())
    for index, row in enumerate(resolver_events):
        requested = row.get("requestedPath")
        if not isinstance(requested, str) or not requested:
            _fail(f"resolver_module_loaded {index} has no requestedPath")
        if requested.replace("/", "\\").casefold().split("\\")[-1] != manifest["resolverModuleName"].casefold():
            _fail(f"resolver_module_loaded {index} requested a different module")
        load_succeeded = row.get("loadSucceeded")
        if not isinstance(load_succeeded, bool):
            _fail(f"resolver_module_loaded {index} loadSucceeded is invalid")
        # LoadLibraryW returns NULL on a normal load failure.  Preserve that
        # observation instead of rejecting the trace before checking the
        # success branch.
        _check_pointer(
            row.get("hModule"),
            f"resolver_module_loaded {index} hModule",
            allow_null=load_succeeded is False,
        )
        if load_succeeded is True:
            observed_handles.add(str(row["hModule"]).casefold())
            module = row.get("module")
            if not isinstance(module, dict):
                _fail(f"resolver_module_loaded {index} has no matching module identity")
            _module_identity(module, f"resolver_module_loaded {index} module", manifest)
            _check_pointer(module.get("base"), f"resolver_module_loaded {index} module.base")
            if module["base"].casefold() != row["hModule"].casefold():
                _fail(f"resolver_module_loaded {index} module.base does not equal hModule")
            if _module_path(module.get("path"), f"resolver_module_loaded {index} module path") != expected_resolver_path:
                _fail(f"resolver_module_loaded {index} module path differs from the pinned file")
            if module.get("size") != manifest["files"]["resolver"]["bytes"]:
                _fail(f"resolver_module_loaded {index} module size differs from the pinned file")
            loaded_identity = row.get("resolverModuleIdentity")
            if not isinstance(loaded_identity, dict):
                _fail(f"resolver_module_loaded {index} has no resolverModuleIdentity")
            _pinned_resolver_identity(
                loaded_identity,
                f"resolver_module_loaded {index} resolverModuleIdentity",
                manifest,
                expected_resolver_path,
            )
            export_map = row.get("resolverExportMap")
            if not isinstance(export_map, list) or len(export_map) != manifest["resolverExportEnumeration"]["hashedCount"]:
                _fail(f"resolver_module_loaded {index} success has incomplete resolver export map")
            canonical = []
            for entry in export_map:
                if not isinstance(entry, dict) or set(entry) != {"name", "offset"}:
                    _fail(f"resolver_module_loaded {index} export map entry schema is invalid")
                if not isinstance(entry["name"], str) or not re.fullmatch(r"[0-9a-f]{32}", entry["name"]):
                    _fail(f"resolver_module_loaded {index} export map contains a non-hashed name")
                if not isinstance(entry["offset"], str) or not re.fullmatch(r"0x[0-9a-fA-F]+", entry["offset"]):
                    _fail(f"resolver_module_loaded {index} export map contains an invalid offset")
                canonical.append(f"{entry['name']}:{int(entry['offset'], 16):x}")
            digest = hashlib.sha256(("\n".join(sorted(canonical)) + "\n").encode()).hexdigest()
            if digest != manifest["resolverExportEnumeration"]["canonicalNameRvaSha256"]:
                _fail(f"resolver_module_loaded {index} export map differs from the pinned manifest")
            if row.get("resolverExportMapCount") != len(export_map):
                _fail(f"resolver_module_loaded {index} export map count drifted")
        else:
            module = row.get("module")
            if not isinstance(module, dict):
                _fail(f"resolver_module_loaded {index} failed load has no module record")
            required_module_keys = {"status", "name", "path", "base", "moduleBase", "size", "exportEnumerationStatus", "hashedExportCount"}
            if set(module) != required_module_keys:
                _fail(f"resolver_module_loaded {index} failed load module schema is not exact")
            if any(module.get(key) is not None for key in ("name", "path", "base", "moduleBase", "size")):
                _fail(f"resolver_module_loaded {index} failed load has non-null module identity")
            if row.get("resolverExportMap") != [] or row.get("resolverExportMapCount") != 0:
                _fail(f"resolver_module_loaded {index} failed load must have no resolver export map")

    target_windows = _target_windows(manifest)
    observed_hashed_events = 0
    attributed_hashed_events = 0
    target_observations = {target_id: 0 for target_id in target_windows}
    request_ordinals: list[int] = []
    for index, row in enumerate(proc_events):
        label = f"get_proc_address {index}"
        handle = row.get("hModule")
        _check_pointer(handle, f"{label}.hModule")
        if str(handle).casefold() not in observed_handles:
            _fail(f"{label} does not match the observed resolver HMODULE")
        ordinal = row.get("requestOrdinal")
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
            _fail(f"{label}.requestOrdinal is invalid")
        request_ordinals.append(ordinal)
        resolver_row_identity = _pinned_resolver_identity(
            row.get("resolverModule"), f"{label}.resolverModule", manifest, expected_resolver_path
        )
        if str(resolver_row_identity.get("base")).casefold() != str(handle).casefold():
            _fail(f"{label}.resolverModule base does not equal hModule")
        name = row.get("lpProcName")
        if name is not None and not isinstance(name, str):
            _fail(f"{label}.lpProcName is not a string or null")
        if row.get("lpProcNameType") not in {"name", "ordinal", "null", "unreadable"}:
            _fail(f"{label}.lpProcNameType is invalid")
        hashed = row.get("requestedExportIsHashed")
        if not isinstance(hashed, bool):
            _fail(f"{label}.requestedExportIsHashed is invalid")
        name_is_hashed = (
            row.get("lpProcNameType") == "name"
            and isinstance(name, str)
            and re.fullmatch(r"[0-9a-fA-F]{32}", name) is not None
        )
        if hashed != name_is_hashed:
            _fail(f"{label}.requestedExportIsHashed disagrees with lpProcName")
        if hashed:
            observed_hashed_events += 1
            if row.get("lpProcNameType") != "name" or not isinstance(name, str) or not re.fullmatch(r"[0-9a-fA-F]{32}", name):
                _fail(f"{label} claims a hashed export without a 32-hex name")
        # GetProcAddress legitimately returns NULL when the export is absent;
        # the trace records that result without treating it as a malformed
        # pointer observation.
        _check_pointer(row.get("returnPointer"), f"{label}.returnPointer", allow_null=True)
        _resolved_fields(row, label)
        if row.get("returnPointer") not in {None, "0x0", "0x0000000000000000"}:
            if _module_name(row.get("resolvedModuleName"), f"{label}.resolvedModuleName") != manifest["resolverModuleName"].casefold():
                _fail(f"{label} returned an address outside the pinned resolver module")
            if _module_path(row.get("resolvedModulePath"), f"{label}.resolvedModulePath") != expected_resolver_path:
                _fail(f"{label} returned an address from a different resolver path")
            if str(row.get("resolvedModuleBase")).casefold() != str(handle).casefold():
                _fail(f"{label}.resolvedModuleBase does not equal hModule")
            if row.get("resolvedModuleSize") != manifest["files"]["resolver"]["bytes"]:
                _fail(f"{label}.resolvedModuleSize differs from the pinned resolver")
            if row.get("resolvedExportStatus") == "enumerated" and row.get("resolvedExportName") is None:
                _fail(f"{label} claims an enumerated export without an export name")
            if row.get("requestedExportIsHashed") and row.get("resolvedExportName") != row.get("lpProcName"):
                _fail(f"{label} hashed request does not resolve to the same enumerated export name")
        backtrace = row.get("callerBacktrace")
        if not isinstance(backtrace, list) or len(backtrace) > manifest["capture"]["maxBacktraceFrames"]:
            _fail(f"{label} caller backtrace exceeds its bound")
        for frame_index, frame_value in enumerate(backtrace):
            _frame(frame_value, f"{label}.callerBacktrace[{frame_index}]")
        caller = row.get("caller")
        if caller is not None:
            _frame(caller, f"{label}.caller")
            if not backtrace or caller != backtrace[0]:
                _fail(f"{label}.caller is not the first callerBacktrace frame")
        elif backtrace:
            _fail(f"{label}.caller is null despite a non-empty callerBacktrace")
        if row.get("callerBacktraceStatus") not in {"frames", "no_resolved_frame", "unavailable"}:
            _fail(f"{label}.callerBacktraceStatus is invalid")
        game_backtrace = row.get("gameAssemblyCallerBacktrace")
        if not isinstance(game_backtrace, list) or len(game_backtrace) > manifest["capture"]["maxBacktraceFrames"]:
            _fail(f"{label} GameAssembly backtrace exceeds its bound")
        for frame_index, frame_value in enumerate(game_backtrace):
            _frame(
                frame_value,
                f"{label}.gameAssemblyCallerBacktrace[{frame_index}]",
                expected_module=manifest["moduleName"],
                expected_path=attached_module_path,
                expected_size=attached_module_size,
                expected_base=gameassembly_module_base,
            )
            if frame_value not in backtrace:
                _fail(f"{label} GameAssembly frame is absent from callerBacktrace")
        if row.get("backtraceStatus") not in {"gameassembly_frames", "no_gameassembly_frame", "unavailable"}:
            _fail(f"{label} backtraceStatus is invalid")
        matches = row.get("targetWindowMatches")
        if not isinstance(matches, list):
            _fail(f"{label}.targetWindowMatches is not a list")
        seen_matches: set[tuple[str, str, str]] = set()
        for match_index, match in enumerate(matches):
            if not isinstance(match, dict):
                _fail(f"{label}.targetWindowMatches[{match_index}] is not an object")
            required = {
                "targetId", "targetMethodIndex", "targetMethodName", "targetFullName", "role",
                "methodIndex", "windowStartOffset", "windowEndOffsetExclusive", "frameAddress", "frameOffset",
            }
            if set(match) != required:
                _fail(f"{label}.targetWindowMatches[{match_index}] schema is not exact")
            target_id = match.get("targetId")
            if target_id not in target_windows:
                _fail(f"{label}.targetWindowMatches[{match_index}] has unknown target")
            role = match.get("role")
            window = target_windows[target_id].get(role)
            if window is None:
                _fail(f"{label}.targetWindowMatches[{match_index}] has unknown target role")
            target = next(target for target in manifest["targets"] if target["id"] == target_id)
            target_fields = {
                "targetMethodIndex": target["methodIndex"],
                "targetMethodName": target["methodName"],
                "targetFullName": target["fullName"],
            }
            for key, expected in target_fields.items():
                if match[key] != expected:
                    _fail(f"{label}.targetWindowMatches[{match_index}] {key} drifted")
            window_fields = {
                "methodIndex": window["methodIndex"],
                "windowStartOffset": window["startOffset"],
                "windowEndOffsetExclusive": window["endOffsetExclusive"],
            }
            for key, expected in window_fields.items():
                if match[key] != expected:
                    _fail(f"{label}.targetWindowMatches[{match_index}] {key} drifted")
            _check_pointer(match["frameAddress"], f"{label}.targetWindowMatches[{match_index}].frameAddress")
            _check_pointer(match["frameOffset"], f"{label}.targetWindowMatches[{match_index}].frameOffset")
            if not any(frame.get("address", "").casefold() == match["frameAddress"].casefold() and frame.get("offset", "").casefold() == match["frameOffset"].casefold() for frame in game_backtrace):
                _fail(f"{label}.targetWindowMatches[{match_index}] frame is absent from GameAssembly backtrace")
            offset = int(match["frameOffset"], 16)
            if not int(window["startOffset"], 16) <= offset < int(window["endOffsetExclusive"], 16):
                _fail(f"{label}.targetWindowMatches[{match_index}] frame lies outside its pinned window")
            key = (target_id, role, match["frameOffset"].casefold())
            if key in seen_matches:
                _fail(f"{label}.targetWindowMatches contains a duplicate match")
            seen_matches.add(key)
            target_observations[target_id] += 1
        expected_targets = list(dict.fromkeys(match["targetId"] for match in matches))
        if row.get("targetAttributionTargets") != expected_targets:
            _fail(f"{label}.targetAttributionTargets does not match targetWindowMatches")
        expected_status = "target_window_match" if expected_targets else "no_target_window_match"
        if row.get("targetAttributionStatus") != expected_status:
            _fail(f"{label}.targetAttributionStatus does not match targetWindowMatches")
        if hashed and matches:
            attributed_hashed_events += 1

    if request_ordinals != list(range(len(request_ordinals))):
        _fail("get_proc_address requestOrdinal values are not contiguous from zero")

    targets_by_id = {target["id"]: target for target in manifest["targets"]}
    pointer_mappings: dict[str, list[dict[str, Any]]] = {
        target_id: [] for target_id in targets_by_id
    }
    seen_pointer_observations: set[tuple[str, str, str, str]] = set()
    calc_line_cpu_observations: list[dict[str, Any]] = []
    for index, row in enumerate(pointer_events):
        label = f"burst_function_pointer {index}"
        target_id = row.get("targetId")
        target = targets_by_id.get(target_id)
        if target is None:
            _fail(f"{label}.targetId is unknown")
        expected_target_fields = {
            "targetMethodIndex": target["methodIndex"],
            "targetMethodName": target["methodName"],
            "targetFullName": target["fullName"],
        }
        for key, expected in expected_target_fields.items():
            if row.get(key) != expected:
                _fail(f"{label}.{key} drifted from the pinned target")
        if row.get("callTargetProbe") != target["callTargetProbe"]:
            _fail(f"{label}.callTargetProbe drifted from the pinned wrapper body")
        return_pointer = row.get("returnPointer")
        _check_pointer(return_pointer, f"{label}.returnPointer", allow_null=True)
        _resolved_fields(row, label)
        cpu_selection = _cpu_selection(
            row.get("cpuSelection"), f"{label}.cpuSelection", manifest,
            expected_resolver_path,
            str(identity_handle) if identity_handle is not None else None,
        )
        cpu_target_id = manifest["calcLineCpuSelection"]["targetId"]
        if target_id == cpu_target_id:
            if cpu_selection["status"] == "not_configured":
                _fail(f"{label}.cpuSelection is missing for the CalcLine target")
            calc_line_cpu_observations.append({
                "returnPointer": return_pointer,
                "resolvedModuleName": row.get("resolvedModuleName"),
                "resolvedModulePath": row.get("resolvedModulePath"),
                "resolvedModuleBase": row.get("resolvedModuleBase"),
                "resolvedModuleSize": row.get("resolvedModuleSize"),
                "resolvedModuleOffset": row.get("resolvedModuleOffset"),
                "resolvedExportName": row.get("resolvedExportName"),
                "resolvedExportStatus": row.get("resolvedExportStatus"),
                "cpuSelection": cpu_selection,
            })
        elif cpu_selection["status"] != "not_configured":
            _fail(f"{label}.cpuSelection is configured for a non-CalcLine target")
        dedupe_key = (
            target_id,
            str(return_pointer).casefold(),
            str(cpu_selection.get("selectedPointer")).casefold(),
            str(cpu_selection.get("status")),
        )
        if dedupe_key in seen_pointer_observations:
            _fail(f"{label} duplicates a target/pointer observation")
        seen_pointer_observations.add(dedupe_key)
        thread_id = row.get("threadId")
        if isinstance(thread_id, bool) or not isinstance(thread_id, int) or thread_id <= 0:
            _fail(f"{label}.threadId is invalid")
        if return_pointer not in {None, "0x0", "0x0000000000000000"}:
            resolved_name = _module_name(row.get("resolvedModuleName"), f"{label}.resolvedModuleName")
            if resolved_name == manifest["resolverModuleName"].casefold():
                if _module_path(row.get("resolvedModulePath"), f"{label}.resolvedModulePath") != expected_resolver_path:
                    _fail(f"{label} resolved to a different resolver path")
                if row.get("resolvedModuleSize") != manifest["files"]["resolver"]["bytes"]:
                    _fail(f"{label}.resolvedModuleSize differs from the pinned resolver")
                if identity_handle is not None and str(row.get("resolvedModuleBase")).casefold() != str(identity_handle).casefold():
                    _fail(f"{label}.resolvedModuleBase differs from the observed resolver HMODULE")
            if row.get("resolvedExportStatus") == "enumerated":
                export_name = row.get("resolvedExportName")
                if resolved_name != manifest["resolverModuleName"].casefold():
                    _fail(f"{label} claims a resolver export outside the resolver module")
                if not isinstance(export_name, str) or not re.fullmatch(r"[0-9a-f]{32}", export_name):
                    _fail(f"{label} enumerated export name is not a 32-hex Burst export")
        pointer_mappings[target_id].append(
            {
                "returnPointer": return_pointer,
                "resolvedModuleName": row.get("resolvedModuleName"),
                "resolvedModulePath": row.get("resolvedModulePath"),
                "resolvedModuleBase": row.get("resolvedModuleBase"),
                "resolvedModuleOffset": row.get("resolvedModuleOffset"),
                "resolvedExportName": row.get("resolvedExportName"),
                "resolvedExportStatus": row.get("resolvedExportStatus"),
                "cpuSelection": cpu_selection,
            }
        )

    cpu_probe = manifest["calcLineCpuSelection"]
    variant_rvas = {
        variant["cpuVariant"]: variant["entryRva"]
        for variant in cpu_probe["variants"]
    }
    cpu_statuses = {
        observation["cpuSelection"]["status"]
        for observation in calc_line_cpu_observations
    }
    observed_variants = {
        observation["cpuSelection"]["selectedCpuVariant"]
        for observation in calc_line_cpu_observations
        if observation["cpuSelection"]["status"] == "matched"
    }
    direct_call_targets_exact = bool(calc_line_cpu_observations) and all(
        observation["returnPointer"] not in {None, "0x0", "0x0000000000000000"}
        and str(observation["resolvedModuleName"]).casefold()
            == manifest["resolverModuleName"].casefold()
        and _module_path(
            observation["resolvedModulePath"],
            "CalcLine direct-call target resolver path",
        ) == expected_resolver_path
        and observation["resolvedModuleSize"]
            == manifest["files"]["resolver"]["bytes"]
        and observation["resolvedExportStatus"] == "enumerated"
        and isinstance(observation["resolvedExportName"], str)
        and re.fullmatch(r"[0-9a-f]{32}", observation["resolvedExportName"])
        for observation in calc_line_cpu_observations
    )
    selected_cpu_variant: str | None = None
    if (
        direct_call_targets_exact and cpu_statuses == {"matched"}
        and len(observed_variants) == 1
    ):
        selected_cpu_variant = next(iter(observed_variants))
        calc_line_cpu_status = "selected_cpu_variant_observed"
    elif not calc_line_cpu_observations:
        calc_line_cpu_status = "missing"
    elif len(cpu_statuses) == 1:
        calc_line_cpu_status = next(iter(cpu_statuses))
    else:
        calc_line_cpu_status = "conflicting_or_incomplete_observations"
    calc_line_cpu_selection = {
        "targetId": cpu_probe["targetId"],
        "functionPointerSlotRva": cpu_probe["functionPointerSlotRva"],
        "observationCount": len(calc_line_cpu_observations),
        "status": calc_line_cpu_status,
        "directCallTargetObserved": direct_call_targets_exact,
        "selectedCpuVariant": selected_cpu_variant,
        "selectedCpuEntryRva": (
            variant_rvas[selected_cpu_variant]
            if selected_cpu_variant is not None else None
        ),
    }

    burst_probe = manifest["routeProbes"]["calcLineBurstEnabled"]
    seen_burst_results: set[bool] = set()
    for index, row in enumerate(burst_gate_events):
        label = f"calc_line_burst_gate {index}"
        if row.get("probe") != "calcLineBurstEnabled":
            _fail(f"{label}.probe is invalid")
        if row.get("methodIndex") != burst_probe["methodIndex"] or row.get("methodName") != burst_probe["methodName"]:
            _fail(f"{label} method identity drifted")
        if row.get("callerReturnOffset") != burst_probe["invokeReturnOffset"]:
            _fail(f"{label} caller return is not the pinned CalcLine Invoke site")
        if row.get("methodInfo") != burst_probe["expectedMethodInfo"] or row.get("returnRegister") != burst_probe["returnRegister"]:
            _fail(f"{label} ABI fields drifted")
        result = row.get("result")
        if not isinstance(result, bool) or result in seen_burst_results:
            _fail(f"{label} result is invalid or duplicated")
        seen_burst_results.add(result)
        thread_id = row.get("threadId")
        if isinstance(thread_id, bool) or not isinstance(thread_id, int) or thread_id <= 0:
            _fail(f"{label}.threadId is invalid")

    ifix_probe = manifest["routeProbes"]["fromToRotationIfix"]
    callers_by_return = {
        caller["returnOffset"]: caller for caller in ifix_probe["calcLineCallerReturns"]
    }
    seen_ifix_results: set[tuple[str, bool]] = set()
    for index, row in enumerate(ifix_gate_events):
        label = f"calc_line_ifix_gate {index}"
        if row.get("probe") != "fromToRotationIfix":
            _fail(f"{label}.probe is invalid")
        if row.get("methodIndex") != ifix_probe["methodIndex"] or row.get("methodName") != ifix_probe["methodName"]:
            _fail(f"{label} method identity drifted")
        if row.get("fromToReturnOffset") != ifix_probe["callReturnOffset"]:
            _fail(f"{label} caller return is not the pinned FromToRotation gate")
        if row.get("patchId") != ifix_probe["patchId"] or row.get("methodInfo") != ifix_probe["expectedMethodInfo"] or row.get("returnRegister") != ifix_probe["returnRegister"]:
            _fail(f"{label} ABI fields drifted")
        caller = callers_by_return.get(row.get("calcLineCallerReturnOffset"))
        if caller is None or row.get("calcLineRoute") != caller["route"]:
            _fail(f"{label} does not carry an admitted CalcLine caller route")
        result = row.get("result")
        key = (caller["route"], result)
        if not isinstance(result, bool) or key in seen_ifix_results:
            _fail(f"{label} result is invalid or duplicated")
        seen_ifix_results.add(key)
        thread_id = row.get("threadId")
        if isinstance(thread_id, bool) or not isinstance(thread_id, int) or thread_id <= 0:
            _fail(f"{label}.threadId is invalid")

    terminal_kinds = {
        "capture_fatal",
        "capture_capped",
        "capture_detached",
        "capture_stop_ack_missing",
        "capture_not_started",
        "capture_start_rejected",
    }
    terminal_rows = [row for row in rows if row.get("kind") in terminal_kinds]
    if terminal_rows:
        _fail(f"trace contains terminal failure state: {terminal_rows[0]}")
    started_rows = [row for row in rows if row.get("kind") == "capture_started"]
    stop_acks = [row for row in rows if row.get("kind") == "capture_stop_ack"]
    if len(started_rows) != 1:
        _fail(f"expected exactly one capture_started row, got {len(started_rows)}")
    if len(stop_acks) != 1:
        _fail(f"expected exactly one capture_stop_ack row, got {len(stop_acks)}")
    stop_ack = stop_acks[0]
    if stop_ack.get("captureStarted") is not True:
        _fail("capture_stop_ack must confirm captureStarted=true")
    if stop_ack.get("terminalState") is not None:
        if stop_ack.get("terminalState") not in {"fatal", "capped", "detached", "start_rejected"}:
            _fail("capture_stop_ack has an unrecognized terminalState")
        _fail("capture_stop_ack confirms a non-clean terminal state")
    expected_event_count = (
        len(resolver_events) + len(proc_events) + len(pointer_events) +
        len(burst_gate_events) + len(ifix_gate_events)
    )
    if stop_ack.get("eventCount") != expected_event_count:
        _fail(
            "capture_stop_ack eventCount differs from resolver/proc/call-target event count: "
            f"expected {expected_event_count}, got {stop_ack.get('eventCount')}"
        )
    stop_identity = stop_ack.get("resolverModuleIdentity")
    _pinned_resolver_identity(
        stop_identity,
        "capture_stop_ack.resolverModuleIdentity",
        manifest,
        expected_resolver_path,
    )
    if ends[0].get("stopAck") is not True or ends[0].get("terminalFailure") is not False:
        _fail("session_end does not confirm a clean stop acknowledgement")
    if expected_event_count > manifest["capture"]["maxEvents"]:
        _fail("trace exceeds configured event cap")

    return {
        "schema": "burstResolverTelemetry.validation.v3",
        "status": "observed_runtime_candidate",
        "trace": str(path.resolve()),
        "sessionId": next(iter(set(session_values))),
        "gameBuild": manifest["gameBuild"],
        "resolverModuleName": manifest["resolverModuleName"],
        "resolverModuleIdentity": resolver_identity,
        "rowCount": len(rows),
        "resolverModuleEventCount": len(resolver_events),
        "getProcAddressEventCount": len(proc_events),
        "burstFunctionPointerEventCount": len(pointer_events),
        "burstFunctionPointerMappings": pointer_mappings,
        "calcLineCpuSelection": calc_line_cpu_selection,
        "calcLineBurstGateObservations": burst_gate_events,
        "calcLineIfixGateObservations": ifix_gate_events,
        "hashedExportRequestCount": observed_hashed_events,
        "hashedExportRequestsWithTargetAttribution": attributed_hashed_events,
        "targetWindowObservations": target_observations,
        "nativeModuleVerified": True,
        "claims": {
            "readOnlyHookEvents": True,
            "resolverModuleIdentityObserved": bool(observed_handles),
            "getProcAddressResolutionObserved": bool(proc_events),
            "liveBurstCallTargetsObserved": all(pointer_mappings.values()),
            "hashedExportRequestsObserved": bool(observed_hashed_events),
            "hashedExportRequestsAttributedToTargetWindows": (
                observed_hashed_events > 0 and attributed_hashed_events == observed_hashed_events
            ),
            "allTargetWindowsObserved": all(target_observations.values()),
            "calcLineBurstSelectionObserved": bool(burst_gate_events),
            "calcLineManagedIfixSelectionObserved": bool(ifix_gate_events),
            "calcLineDirectCallTargetObserved": direct_call_targets_exact,
            "calcLineSelectedCpuVariantObserved": (
                selected_cpu_variant is not None
            ),
            "gameAssemblyCallerBacktraceObserved": any(
                row.get("backtraceStatus") == "gameassembly_frames" and row.get("gameAssemblyCallerBacktrace")
                for row in proc_events
            ),
            "resolverExportMappingProven": all(
                any(
                    mapping["resolvedExportStatus"] == "enumerated"
                    and mapping["resolvedExportName"] is not None
                    for mapping in mappings
                )
                for mappings in pointer_mappings.values()
            ),
            "gameStateWritten": False,
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
        print(f"Burst resolver telemetry validation failed: {exc}", file=sys.stderr)
        return 1
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "resolverModuleEventCount": result["resolverModuleEventCount"],
                "getProcAddressEventCount": result["getProcAddressEventCount"],
                "burstFunctionPointerEventCount": result["burstFunctionPointerEventCount"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
