"""Stage and (optionally) launch an authorized read-only native audio capture.

This module is intentionally a launcher, not a second audio hook manifest.  The
managed/native hook contract and the build file hashes are owned by
``runtime_trace_audio_capture`` and are always validated through that module.
The native payload is supplied by the caller; this launcher does not contain
native addresses or attempt to discover them.

``--check-only`` is the safe default for preparing a capture.  It verifies the
selected game files, the existing manifest's hook ranges, and an optional
payload, without importing ``pyinjector``, enumerating processes, or writing a
package/session.  A non-check invocation must explicitly request package or
session staging, or ``--inject``.  Injection is one ordinary pyinjector call;
an access denial is reported and never retried.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from . import runtime_trace_audio_capture as audio_capture
from . import runtime_trace_core as core


DEFAULT_MANIFEST = audio_capture.DEFAULT_MANIFEST
DEFAULT_AGENT = audio_capture.DEFAULT_AGENT
SESSION_SCHEMA = "audioRuntimeTrace.session.v1"
STAGED_PAYLOAD_NAME = "audio_capture.dll"
SESSION_CONFIG_NAME = "audio_capture.session.json"
DEFAULT_HEARTBEAT_MS = 250
DEFAULT_WAIT_TIMEOUT_MS = 15_000
MIN_HEARTBEAT_MS = 100
MAX_HEARTBEAT_MS = 60_000
MIN_WAIT_TIMEOUT_MS = 1
MAX_WAIT_TIMEOUT_MS = 3_600_000
CAPTURE_TOOL = "authorized-audio-native-capture-launcher/1"
HOOK_PROFILE = "audio_chain_v1"
HOOK_PROFILE_FIELDS = {
    "AudioAdapter._PostEventWithExternalSource": "managed_external_source_rva",
    "AkSoundEngine.SourceMediaLookup": "source_media_lookup_rva",
    "AkSoundEngine.DefaultIoOpenDispatch": "default_io_open_rva",
}
_SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")


class NativeCaptureConfigurationError(core.CaptureConfigurationError):
    """Raised before staging or injection when the capture is unsafe."""


@dataclass(frozen=True)
class NativeCapturePlan:
    """Hash-verified inputs shared by package and session staging."""

    game_root: Path
    manifest_path: Path
    manifest: dict[str, Any]
    verified: dict[str, Path]
    manifest_sha256: str
    agent_sha256: str
    payload: Path | None = None
    payload_sha256: str | None = None

    @property
    def game_build(self) -> str:
        return self.manifest["gameBuild"]


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Add launcher options to an existing parser or the standalone CLI."""

    parser.add_argument(
        "--game-root",
        type=Path,
        default=None,
        help="Selected game install root containing Endfield_Data.",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--agent", type=Path, default=DEFAULT_AGENT)
    parser.add_argument(
        "--native-library",
        "--payload",
        dest="native_library",
        type=Path,
        help="Optional native read-only capture DLL to hash and stage/inject.",
    )
    parser.add_argument(
        "--package-dir",
        type=Path,
        help="Private staging directory for audio_capture.dll and its session JSON.",
    )
    parser.add_argument(
        "--session-dir",
        type=Path,
        help="Compatibility alias for the session/package staging directory.",
    )
    parser.add_argument(
        "--session-id",
        help="Stable staging identifier (letters, digits, '.', '_' and '-').",
    )
    parser.add_argument("--pid", type=int, help="Existing target PID for one injection attempt.")
    parser.add_argument("--output", type=Path, help="Event-v1 JSONL path written by the native DLL.")
    parser.add_argument("--diagnostics", type=Path, help="Diagnostics JSONL path written by the native DLL.")
    parser.add_argument("--heartbeat-ms", type=int, default=DEFAULT_HEARTBEAT_MS)
    parser.add_argument("--wait-timeout-ms", type=int, default=DEFAULT_WAIT_TIMEOUT_MS)
    parser.add_argument(
        "--inject",
        action="store_true",
        help="After validation/staging, make one ordinary pyinjector LoadLibrary attempt.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate inputs only; never import pyinjector, enumerate, attach, inject, or write.",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    return parser.parse_args(argv)


def _sha256(path: Path) -> str:
    try:
        return core.sha256_file(path)
    except OSError as exc:
        raise NativeCaptureConfigurationError(f"cannot hash capture input: {path}: {exc}") from exc


def _selected_game_root(value: Path | None) -> Path:
    if value is not None:
        return value.resolve()
    try:
        return core.resolve_installed_game_data_root().parent.resolve()
    except (OSError, RuntimeError) as exc:
        raise NativeCaptureConfigurationError(
            "--game-root is required when the installed game root cannot be resolved"
        ) from exc


def _validate_session_id(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).strftime("audio-native-%Y%m%dT%H%M%SZ")
    if not _SESSION_ID.fullmatch(value):
        raise NativeCaptureConfigurationError(
            "--session-id must be 1-96 characters from A-Z, a-z, 0-9, '.', '_' or '-'; "
            "it must not contain path separators"
        )
    return value


def _validate_manifest_containment(game_root: Path, manifest: dict[str, Any]) -> None:
    """Reject manifest paths which resolve outside the selected game root."""

    root = game_root.resolve()
    for name, entry in manifest.get("files", {}).items():
        relative = entry.get("relativePath") if isinstance(entry, dict) else None
        if not isinstance(relative, str) or not relative:
            raise NativeCaptureConfigurationError(
                f"manifest file {name!r} has no usable relativePath"
            )
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise NativeCaptureConfigurationError(
                f"manifest file {name!r} escapes selected game root: {relative!r}"
            ) from exc


def validate_payload_pe_x64(path: Path) -> None:
    """Validate the inexpensive PE/COFF x64 identity without external deps."""

    try:
        with path.open("rb") as handle:
            dos = handle.read(0x40)
            if len(dos) < 0x40 or dos[:2] != b"MZ":
                raise NativeCaptureConfigurationError(f"native payload is not a PE file: {path}")
            pe_offset = int.from_bytes(dos[0x3C:0x40], "little")
            if pe_offset < 0x40:
                raise NativeCaptureConfigurationError(f"native payload has an invalid PE offset: {path}")
            handle.seek(pe_offset)
            header = handle.read(26)
    except OSError as exc:
        raise NativeCaptureConfigurationError(f"cannot read native payload: {path}: {exc}") from exc
    if len(header) < 26 or header[:4] != b"PE\0\0":
        raise NativeCaptureConfigurationError(f"native payload is not a PE image: {path}")
    machine = int.from_bytes(header[4:6], "little")
    optional_magic = int.from_bytes(header[24:26], "little")
    if machine != 0x8664 or optional_magic != 0x20B:
        raise NativeCaptureConfigurationError(
            f"native payload must be PE32+ x64 (machine=0x{machine:x}, optional=0x{optional_magic:x}): {path}"
        )


def _validate_payload(path: Path | None) -> tuple[Path | None, str | None]:
    if path is None:
        return None, None
    resolved = path.resolve()
    if not resolved.is_file():
        raise NativeCaptureConfigurationError(f"native capture payload not found: {resolved}")
    if resolved.suffix.casefold() != ".dll":
        raise NativeCaptureConfigurationError(f"native capture payload must be a .dll: {resolved}")
    validate_payload_pe_x64(resolved)
    return resolved, _sha256(resolved)


def _native_hook_profile(manifest: dict[str, Any]) -> dict[str, int | str]:
    """Resolve one native profile from the canonical hook manifest."""

    profiles = manifest.get("nativeCaptureProfiles")
    profile = profiles.get(HOOK_PROFILE) if isinstance(profiles, dict) else None
    enabled = profile.get("enabled") if isinstance(profile, dict) else None
    if not isinstance(enabled, list) or enabled != list(HOOK_PROFILE_FIELDS):
        raise NativeCaptureConfigurationError(
            f"manifest {HOOK_PROFILE!r} profile must enable the maintained three-hook order"
        )
    entries: dict[str, dict[str, Any]] = {}
    for collection_name in ("hooks", "nativeHooks"):
        collection = manifest.get(collection_name)
        if not isinstance(collection, list):
            continue
        for entry in collection:
            if isinstance(entry, dict) and entry.get("name") in HOOK_PROFILE_FIELDS:
                name = str(entry["name"])
                if name in entries:
                    raise NativeCaptureConfigurationError(f"duplicate hook contract: {name}")
                entries[name] = entry
    result: dict[str, int | str] = {"hook_profile": HOOK_PROFILE}
    for name, field in HOOK_PROFILE_FIELDS.items():
        entry = entries.get(name)
        raw_rva = entry.get("rva") if entry else None
        if not isinstance(raw_rva, str):
            raise NativeCaptureConfigurationError(f"profile hook has no RVA: {name}")
        try:
            rva = int(raw_rva, 0)
        except ValueError as exc:
            raise NativeCaptureConfigurationError(f"profile hook has invalid RVA: {name}") from exc
        if rva <= 0:
            raise NativeCaptureConfigurationError(f"profile hook has non-positive RVA: {name}")
        result[field] = rva
    return result


def prepare_plan(args: argparse.Namespace) -> NativeCapturePlan:
    """Verify all static inputs and return one immutable capture plan."""

    if getattr(args, "check_only", False) and getattr(args, "inject", False):
        raise NativeCaptureConfigurationError("--check-only cannot be combined with --inject")
    manifest_path = Path(args.manifest).resolve()
    agent_path = Path(args.agent).resolve()
    game_root = _selected_game_root(getattr(args, "game_root", None))
    try:
        manifest = audio_capture.load_manifest(manifest_path)
        if not manifest.get("nativeHooks") or not manifest.get("nativeModuleName"):
            raise NativeCaptureConfigurationError(
                "audio manifest has no native hook contract; refusing native capture"
            )
        _validate_manifest_containment(game_root, manifest)
        verified = core.verify_game_files(game_root, manifest)
        audio_capture.validate_hook_ranges(
            manifest, verified["gameAssembly"], verified.get("akSoundEngine")
        )
        # Rendering validates the existing managed agent/template contract but
        # does not load Frida or execute any code.
        rendered = audio_capture.render_agent_source(agent_path, manifest)
    except (KeyError, OSError, RuntimeError) as exc:
        if isinstance(exc, core.CaptureConfigurationError):
            raise
        raise NativeCaptureConfigurationError(str(exc)) from exc
    payload, payload_sha256 = _validate_payload(getattr(args, "native_library", None))
    return NativeCapturePlan(
        game_root=game_root,
        manifest_path=manifest_path,
        manifest=manifest,
        verified=verified,
        manifest_sha256=_sha256(manifest_path),
        agent_sha256=hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        payload=payload,
        payload_sha256=payload_sha256,
    )


def _write_json(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise NativeCaptureConfigurationError(f"cannot stage {path}: {exc}") from exc
    return path


def stage_payload(plan: NativeCapturePlan, directory: Path) -> Path:
    """Copy the verified payload into a private, fixed-compatible DLL name."""

    if plan.payload is None:
        raise NativeCaptureConfigurationError("package staging requires --native-library/--payload")
    target_dir = directory.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / STAGED_PAYLOAD_NAME
    source = plan.payload.resolve()
    if source == target:
        raise NativeCaptureConfigurationError("payload must be copied to a private staging path")
    before = _sha256(source)
    if target.exists():
        if not target.is_file() or _sha256(target) != before:
            raise NativeCaptureConfigurationError(
                f"refusing to overwrite a different staged payload: {target}"
            )
    else:
        try:
            shutil.copyfile(source, target)
        except OSError as exc:
            raise NativeCaptureConfigurationError(f"cannot stage native payload: {target}: {exc}") from exc
    after = _sha256(source)
    staged_hash = _sha256(target)
    if before != after or staged_hash != after:
        raise NativeCaptureConfigurationError(
            "native payload changed while staging or staged payload hash does not match source"
        )
    validate_payload_pe_x64(target)
    return target


def _default_output_paths(directory: Path) -> tuple[Path, Path]:
    output = directory.resolve() / "audio_capture.jsonl"
    return output, core.diagnostics_path(output)


def session_record(
    plan: NativeCapturePlan,
    directory: Path,
    *,
    session_id: str | None = None,
    output_path: Path | None = None,
    diagnostics_path: Path | None = None,
    pid: int | None = None,
    heartbeat_ms: int = DEFAULT_HEARTBEAT_MS,
    wait_timeout_ms: int = DEFAULT_WAIT_TIMEOUT_MS,
) -> dict[str, Any]:
    """Build the snake_case session contract consumed by the native DLL."""

    if pid is not None and pid <= 0:
        raise NativeCaptureConfigurationError("--pid must be a positive integer")
    if not MIN_HEARTBEAT_MS <= heartbeat_ms <= MAX_HEARTBEAT_MS:
        raise NativeCaptureConfigurationError(
            f"heartbeat_ms must be in {MIN_HEARTBEAT_MS}..{MAX_HEARTBEAT_MS}"
        )
    if not MIN_WAIT_TIMEOUT_MS <= wait_timeout_ms <= MAX_WAIT_TIMEOUT_MS:
        raise NativeCaptureConfigurationError(
            f"wait_timeout_ms must be in {MIN_WAIT_TIMEOUT_MS}..{MAX_WAIT_TIMEOUT_MS}"
        )
    language = plan.manifest.get("language")
    if not isinstance(language, str) or not language.strip():
        raise NativeCaptureConfigurationError(
            "audio manifest language must be non-empty before native session staging"
        )
    default_output, default_diagnostics = _default_output_paths(directory)
    output = (output_path or default_output).resolve()
    diagnostics = (diagnostics_path or default_diagnostics).resolve()
    if plan.payload is None:
        raise NativeCaptureConfigurationError("session staging requires --native-library/--payload")
    game_assembly = plan.verified["gameAssembly"]
    native = plan.verified["akSoundEngine"]
    record = {
        "schema": SESSION_SCHEMA,
        "session_id": _validate_session_id(session_id),
        "output_path": str(output),
        "diagnostics_path": str(diagnostics),
        "game_build": plan.game_build,
        "capture_tool": CAPTURE_TOOL,
        "export_fingerprint": plan.manifest["files"]["metadata"]["sha256"],
        "language": language.strip(),
        "selected_game_root": str(plan.game_root),
        "expected_process_name": plan.manifest["processName"],
        "module_name": plan.manifest["moduleName"],
        "expected_module_path": str(game_assembly),
        "expected_module_size": game_assembly.stat().st_size,
        "expected_module_sha256": plan.manifest["files"]["gameAssembly"]["sha256"],
        "native_module_name": plan.manifest["nativeModuleName"],
        "expected_native_module_path": str(native),
        "expected_native_module_size": native.stat().st_size,
        "expected_native_module_sha256": plan.manifest["files"]["akSoundEngine"]["sha256"],
        "heartbeat_ms": heartbeat_ms,
        "wait_timeout_ms": wait_timeout_ms,
    }
    record.update(_native_hook_profile(plan.manifest))
    return record


def stage_session(
    plan: NativeCapturePlan,
    directory: Path,
    *,
    session_id: str | None = None,
    output_path: Path | None = None,
    diagnostics_path: Path | None = None,
    pid: int | None = None,
    heartbeat_ms: int = DEFAULT_HEARTBEAT_MS,
    wait_timeout_ms: int = DEFAULT_WAIT_TIMEOUT_MS,
) -> Path:
    """Write audio_capture.session.json beside the staged DLL."""

    record = session_record(
        plan,
        directory,
        session_id=session_id,
        output_path=output_path,
        diagnostics_path=diagnostics_path,
        pid=pid,
        heartbeat_ms=heartbeat_ms,
        wait_timeout_ms=wait_timeout_ms,
    )
    # Validate the complete contract before creating the staging directory or
    # copying a payload; malformed bounds/language must have no write side effect.
    stage_payload(plan, directory)
    target = directory.resolve() / SESSION_CONFIG_NAME
    if target.is_file():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise NativeCaptureConfigurationError(f"existing session is not valid JSON: {target}") from exc
        if existing != record:
            raise NativeCaptureConfigurationError(
                f"refusing to overwrite a different staged session: {target}"
            )
        return target
    return _write_json(target, record)


def stage_package(
    plan: NativeCapturePlan,
    directory: Path,
    *,
    session_id: str | None = None,
    output_path: Path | None = None,
    diagnostics_path: Path | None = None,
    pid: int | None = None,
    heartbeat_ms: int = DEFAULT_HEARTBEAT_MS,
    wait_timeout_ms: int = DEFAULT_WAIT_TIMEOUT_MS,
) -> Path:
    """Stage the private DLL and adjacent native-agent session contract."""

    return stage_session(
        plan,
        directory,
        session_id=session_id,
        output_path=output_path,
        diagnostics_path=diagnostics_path,
        pid=pid,
        heartbeat_ms=heartbeat_ms,
        wait_timeout_ms=wait_timeout_ms,
    )


def verify_target_pid(pid: int, process_name: str) -> None:
    """Verify a target using the ordinary Windows process listing."""

    if pid <= 0:
        raise NativeCaptureConfigurationError("--pid must be a positive integer")
    try:
        result = subprocess.run(
            ["tasklist.exe", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise NativeCaptureConfigurationError(f"could not verify target PID {pid}: {exc}") from exc
    rows = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode or len(rows) != 1:
        raise NativeCaptureConfigurationError(f"could not verify Windows process PID {pid}")
    fields = next(csv.reader([rows[0]]), [])
    if (
        len(fields) < 2
        or fields[0].casefold() != process_name.casefold()
        or fields[1].replace(",", "") != str(pid)
    ):
        actual = fields[0] if fields else "unknown"
        raise NativeCaptureConfigurationError(f"PID {pid} is {actual!r}, expected {process_name!r}")


def inject_once(pid: int, payload: Path) -> None:
    """Make exactly one ordinary pyinjector call, with no retry/evasion path."""

    try:
        import pyinjector  # type: ignore
    except ImportError as exc:
        raise NativeCaptureConfigurationError(
            "pyinjector is required only for --inject; install it in the capture environment"
        ) from exc
    inject = getattr(pyinjector, "inject", None)
    if not callable(inject):
        raise NativeCaptureConfigurationError("pyinjector does not expose inject(pid, library)")
    try:
        inject(pid, str(payload))
    except Exception as exc:
        # Deliberately one call: denial is a terminal result, not an invitation
        # to retry under another API, privilege, or process-creation path.
        detail = str(exc).strip() or type(exc).__name__
        raise NativeCaptureConfigurationError(
            f"ordinary LoadLibrary injection was refused for PID {pid}: {detail}; stopped without retry"
        ) from exc


def _handshake_matches_session(row: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Require the native header to echo every hash/path/process fact we staged."""

    def same_path(returned: Any, staged: Any) -> bool:
        return (
            isinstance(returned, str)
            and isinstance(staged, str)
            and core.normalized_path(returned) == core.normalized_path(staged)
        )

    if row.get("gameBuild") != expected.get("game_build"):
        return False
    if not same_path(row.get("selectedGameRoot"), expected.get("selected_game_root")):
        return False
    process_name = row.get("processName")
    if process_name is None:
        process_name = row.get("expectedProcessName")
    if not isinstance(process_name, str) or process_name.casefold() != str(
        expected.get("expected_process_name", "")
    ).casefold():
        return False
    path_pairs = (
        ("expectedModulePath", "expected_module_path"),
        ("expectedNativeModulePath", "expected_native_module_path"),
    )
    for returned, staged in path_pairs:
        if not same_path(row.get(returned), expected.get(staged)):
            return False
    hash_pairs = (
        ("expectedModuleSha256", "expected_module_sha256"),
        ("expectedNativeModuleSha256", "expected_native_module_sha256"),
    )
    for returned, staged in hash_pairs:
        value = row.get(returned)
        if not isinstance(value, str) or value.casefold() != str(expected.get(staged, "")).casefold():
            return False
    size_pairs = (
        ("expectedModuleSize", "expected_module_size"),
        ("expectedNativeModuleSize", "expected_native_module_size"),
    )
    for returned, staged in size_pairs:
        value = row.get(returned)
        if isinstance(value, bool) or not isinstance(value, int) or value != expected.get(staged):
            return False
    return True


def wait_for_session_start(
    output_path: Path,
    session_id: str,
    timeout_ms: int,
    *,
    poll_ms: int = 100,
    expected_game_build: str | None = None,
    expected_session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Poll one bounded output stream for an importer-compatible handshake."""

    if not MIN_WAIT_TIMEOUT_MS <= timeout_ms <= MAX_WAIT_TIMEOUT_MS or poll_ms <= 0:
        raise NativeCaptureConfigurationError(
            f"handshake timeout must be in {MIN_WAIT_TIMEOUT_MS}..{MAX_WAIT_TIMEOUT_MS} ms"
        )
    import time

    deadline = time.monotonic() + timeout_ms / 1000
    offset = 0
    partial = ""
    while time.monotonic() < deadline:
        if output_path.is_file():
            try:
                with output_path.open("r", encoding="utf-8") as handle:
                    handle.seek(offset)
                    partial += handle.read()
                    offset = handle.tell()
            except OSError as exc:
                raise NativeCaptureConfigurationError(
                    f"cannot read native capture handshake output: {output_path}: {exc}"
                ) from exc
            lines = partial.splitlines(keepends=True)
            partial = lines.pop() if lines and not lines[-1].endswith(("\n", "\r")) else ""
            for line in lines:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict) or row.get("kind") != "session_start":
                    continue
                if row.get("schema") != audio_capture.EVENT_SCHEMA:
                    continue
                if row.get("sessionId") != session_id:
                    raise NativeCaptureConfigurationError(
                        "native capture handshake belongs to a different session"
                    )
                if expected_game_build is not None and row.get("gameBuild") != expected_game_build:
                    continue
                if expected_session is not None and not _handshake_matches_session(
                    row, expected_session
                ):
                    continue
                if not isinstance(row.get("gameBuild"), str) or not isinstance(
                    row.get("captureTool"), str
                ):
                    continue
                if isinstance(row.get("seq"), bool) or not isinstance(row.get("seq"), int):
                    continue
                if isinstance(row.get("monotonicMs"), bool) or not isinstance(
                    row.get("monotonicMs"), (int, float)
                ) or row.get("monotonicMs") < 0:
                    continue
                required_gates = (
                    "processNameMatch",
                    "modulePathMatch",
                    "moduleSizeMatch",
                    "moduleSha256Match",
                    "nativeModulePathMatch",
                    "nativeModuleSizeMatch",
                    "nativeModuleSha256Match",
                )
                if any(row.get(key) is not True for key in required_gates):
                    continue
                return row
        time.sleep(poll_ms / 1000)
    raise NativeCaptureConfigurationError(
        f"native capture did not emit an importer-compatible session_start within {timeout_ms} ms"
    )


def run(args: argparse.Namespace) -> int:
    plan = prepare_plan(args)
    if args.check_only:
        print(
            f"Checked {plan.game_build}: {len(plan.verified)} hash-locked files, "
            f"{len(plan.manifest['hooks'])} managed and "
            f"{len(plan.manifest.get('nativeHooks', []))} native hooks; "
            "no process, pyinjector, package, or session access performed."
        )
        return 0
    staging_dir = args.package_dir or args.session_dir
    if not (staging_dir or args.inject):
        raise NativeCaptureConfigurationError(
            "no action requested; use --check-only, --package-dir/--session-dir, or --inject"
        )
    # Complete all injection preflight before writing a package/session.  This
    # keeps a denied or malformed request from looking like an armed session.
    if args.inject:
        if args.package_dir is None:
            raise NativeCaptureConfigurationError("--inject requires --package-dir")
        if plan.payload is None:
            raise NativeCaptureConfigurationError("--inject requires --native-library/--payload")
        if args.pid is None:
            raise NativeCaptureConfigurationError("--inject requires --pid; process discovery is disabled")
        verify_target_pid(args.pid, plan.manifest["processName"])
    if staging_dir is None:
        raise NativeCaptureConfigurationError("staging directory is required")
    session_path = stage_package(
        plan,
        staging_dir,
        session_id=args.session_id,
        output_path=args.output,
        diagnostics_path=args.diagnostics,
        pid=args.pid,
        heartbeat_ms=args.heartbeat_ms,
        wait_timeout_ms=args.wait_timeout_ms,
    )
    if args.inject:
        staged_payload = session_path.parent / STAGED_PAYLOAD_NAME
        # Rehash the private copy immediately before the sole injection call.
        # The session contract has already fixed this path and no source path
        # is passed to pyinjector.
        expected_payload_hash = _sha256(staged_payload)
        if expected_payload_hash != _sha256(plan.payload):
            raise NativeCaptureConfigurationError(
                "staged native payload changed before injection; refusing to inject"
            )
        inject_once(args.pid, staged_payload)
        try:
            staged_session = json.loads(session_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise NativeCaptureConfigurationError(
                f"cannot read staged native session contract: {session_path}"
            ) from exc
        handshake = wait_for_session_start(
            Path(staged_session["output_path"]),
            staged_session["session_id"],
            args.wait_timeout_ms,
            poll_ms=max(50, min(args.heartbeat_ms, 500)),
            expected_game_build=plan.game_build,
            expected_session=staged_session,
        )
        print(
            f"One ordinary read-only capture injection attempt completed for PID {args.pid}; "
            f"session_start observed for {handshake['sessionId']}."
        )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(parse_args(argv))
    except (NativeCaptureConfigurationError, core.CaptureConfigurationError, OSError, RuntimeError) as exc:
        print(f"Audio native capture launcher failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
