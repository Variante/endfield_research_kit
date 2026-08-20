"""Fail-closed validator for Burst resolver telemetry JSONL captures."""
from __future__ import annotations

import argparse
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
            "modulePathMatch", "moduleSizeMatch", "verifiedFiles", "hookStates",
            "kernel32ModuleName", "resolverModuleName", "resolverModuleIdentity",
            "resolverExpectedPath", "resolverExpectedSize", "gameAssemblyModuleName",
            "gameAssemblyModuleBase", "gameAssemblyModuleSize", "targets",
            "resolverExportMapSha256", "resolverExportMapCount",
        },
        "resolver_module_loaded": {
            "requestedPath", "hModule", "loadSucceeded", "module", "resolverModuleIdentity",
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
    if any(kind not in {"resolver_module_loaded", "get_proc_address"} for kind in middle_kinds):
        _fail("resolver/proc events are only valid between capture_started and capture_stop_ack")

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
        else:
            module = row.get("module")
            if not isinstance(module, dict):
                _fail(f"resolver_module_loaded {index} failed load has no module record")
            required_module_keys = {"status", "name", "path", "base", "moduleBase", "size", "exportEnumerationStatus", "hashedExportCount"}
            if set(module) != required_module_keys:
                _fail(f"resolver_module_loaded {index} failed load module schema is not exact")
            if any(module.get(key) is not None for key in ("name", "path", "base", "moduleBase", "size")):
                _fail(f"resolver_module_loaded {index} failed load has non-null module identity")

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
    expected_event_count = len(resolver_events) + len(proc_events)
    if stop_ack.get("eventCount") != expected_event_count:
        _fail(
            "capture_stop_ack eventCount differs from resolver/proc event count: "
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
    if len(resolver_events) + len(proc_events) > manifest["capture"]["maxEvents"]:
        _fail("trace exceeds configured event cap")

    return {
        "schema": "burstResolverTelemetry.validation.v1",
        "status": "observed_runtime_candidate",
        "trace": str(path.resolve()),
        "sessionId": next(iter(set(session_values))),
        "gameBuild": manifest["gameBuild"],
        "resolverModuleName": manifest["resolverModuleName"],
        "resolverModuleIdentity": resolver_identity,
        "rowCount": len(rows),
        "resolverModuleEventCount": len(resolver_events),
        "getProcAddressEventCount": len(proc_events),
        "hashedExportRequestCount": observed_hashed_events,
        "hashedExportRequestsWithTargetAttribution": attributed_hashed_events,
        "targetWindowObservations": target_observations,
        "nativeModuleVerified": True,
        "claims": {
            "readOnlyHookEvents": True,
            "resolverModuleIdentityObserved": bool(observed_handles),
            "getProcAddressResolutionObserved": bool(proc_events),
            "hashedExportRequestsObserved": bool(observed_hashed_events),
            "hashedExportRequestsAttributedToTargetWindows": (
                observed_hashed_events > 0 and attributed_hashed_events == observed_hashed_events
            ),
            "allThreeTargetWindowsObserved": all(target_observations.values()),
            "gameAssemblyCallerBacktraceObserved": any(
                row.get("backtraceStatus") == "gameassembly_frames" and row.get("gameAssemblyCallerBacktrace")
                for row in proc_events
            ),
            "resolverExportMappingProven": False,
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
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
