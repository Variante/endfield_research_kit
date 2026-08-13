"""Shared fail-closed infrastructure for runtime trace capture and import."""
from __future__ import annotations

import csv
import io
import json
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

if __package__ == "scripts.story_recovery":
    from ..common import resolve_installed_game_data_root, sha256_file
elif __package__ == "story_recovery":
    from common import resolve_installed_game_data_root, sha256_file
else:  # pragma: no cover - invalid embedding identity
    raise ImportError(f"unsupported package identity: {__package__!r}")


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GAME_ROOT = resolve_installed_game_data_root().parent


class CaptureConfigurationError(RuntimeError):
    """Raised when a local build or hook configuration is unsafe."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def default_capture_output(profile: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "scratch" / "story" / "runtime_trace" / f"{profile}-runtime-{stamp}.jsonl"


def load_manifest_object(path: Path, schema: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CaptureConfigurationError(f"{label} manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CaptureConfigurationError(f"invalid {label} manifest JSON: {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema") != schema:
        raise CaptureConfigurationError(f"{label} manifest schema must be {schema!r}")
    return value


def verify_game_files(game_root: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise CaptureConfigurationError("manifest must contain a non-empty files object")
    verified: dict[str, Path] = {}
    for name, expected in files.items():
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
        path = (game_root / relative_path).resolve()
        if not path.is_file():
            raise CaptureConfigurationError(f"required game file not found: {path}")
        actual_size = path.stat().st_size
        if actual_size != expected_size:
            raise CaptureConfigurationError(
                f"refusing hooks: {name} size changed: expected {expected_size}, got {actual_size}"
            )
        actual_hash = sha256_file(path)
        if actual_hash.casefold() != expected_hash.casefold():
            raise CaptureConfigurationError(
                f"refusing hooks: {name} SHA-256 changed: expected {expected_hash}, got {actual_hash}"
            )
        verified[name] = path
    return verified


def render_agent_template(
    path: Path,
    placeholder: str,
    config: dict[str, Any],
    label: str,
) -> str:
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CaptureConfigurationError(f"{label} Frida agent not found: {path}") from exc
    if source.count(placeholder) != 1:
        raise CaptureConfigurationError(
            f"{label} Frida agent must contain exactly one {placeholder} placeholder"
        )
    return source.replace(
        placeholder,
        json.dumps(config, ensure_ascii=False, separators=(",", ":")),
    )


def diagnostics_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.diagnostics.jsonl")


class EventWriter:
    """Thread-safe writer for one primary event stream plus optional side streams."""

    def __init__(
        self,
        output: Path,
        session_id: str,
        start: float,
        event_schema: str,
        side_streams: dict[str, tuple[Path, str]] | None = None,
    ) -> None:
        self.output = output
        self.diagnostics = diagnostics_path(output)
        self.session_id = session_id
        self.start = start
        self.schemas = {"event": event_schema}
        self.paths = {"event": output}
        for channel, (path, schema) in (side_streams or {}).items():
            self.paths[channel] = path
            self.schemas[channel] = schema
        self.counts = {channel: 0 for channel in self.paths}
        self.sequences = {channel: 0 for channel in self.paths}
        self.diagnostic_count = 0
        self.lock = threading.Lock()
        output.parent.mkdir(parents=True, exist_ok=True)
        self.handles = {
            channel: path.open("w", encoding="utf-8", newline="\n")
            for channel, path in self.paths.items()
        }
        self.diagnostic_handle = self.diagnostics.open("w", encoding="utf-8", newline="\n")

    @staticmethod
    def _write(handle: Any, value: dict[str, Any]) -> None:
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()

    def emit(
        self,
        kind: str,
        values: dict[str, Any] | None = None,
        *,
        channel: str = "event",
    ) -> None:
        with self.lock:
            row = {
                **dict(values or {}),
                "schema": self.schemas[channel],
                "sessionId": self.session_id,
                "seq": self.sequences[channel],
                "monotonicMs": round((time.perf_counter() - self.start) * 1000, 3),
                "utc": utc_now(),
                "kind": kind,
            }
            self._write(self.handles[channel], row)
            self.sequences[channel] += 1
            self.counts[channel] += 1

    def diagnostic(self, kind: str, values: dict[str, Any] | None = None) -> None:
        with self.lock:
            self._write(
                self.diagnostic_handle,
                {
                    "utc": utc_now(),
                    "monotonicMs": round((time.perf_counter() - self.start) * 1000, 3),
                    "sessionId": self.session_id,
                    "kind": kind,
                    **dict(values or {}),
                },
            )
            self.diagnostic_count += 1

    def close(self) -> None:
        for handle in self.handles.values():
            handle.close()
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
        raise CaptureConfigurationError(f"PID {pid} is {image_name!r}, expected {process_name!r}")
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
            raise RuntimeError(f"timed out waiting for runtime modules: {', '.join(module_names)}")
        if failure:
            raise RuntimeError(f"module-wait agent failed: {failure[0]}")
    finally:
        probe.unload()


def install_stop_signal(stop: threading.Event) -> Any:
    previous = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, lambda _signum, _frame: stop.set())
    return previous


def restore_stop_signal(previous: Any) -> None:
    signal.signal(signal.SIGINT, previous)


def normalized_path(value: str | Path) -> str:
    return str(Path(value).resolve()).replace("/", "\\").casefold()


def validate_attached_module(ready_payload: dict[str, Any], expected_module: Path) -> dict[str, Any]:
    actual_path = ready_payload.get("modulePath")
    actual_size = ready_payload.get("moduleSize")
    expected_path = expected_module.resolve()
    expected_size = expected_path.stat().st_size
    if not isinstance(actual_path, str) or not actual_path.strip():
        raise RuntimeError("Frida agent did not report the attached GameAssembly path")
    if isinstance(actual_size, bool) or not isinstance(actual_size, int) or actual_size <= 0:
        raise RuntimeError("Frida agent did not report a valid attached GameAssembly size")
    facts = {
        "expectedModulePath": str(expected_path),
        "expectedModuleSize": expected_size,
        "attachedModulePath": actual_path,
        "attachedModuleSize": actual_size,
        "modulePathMatch": normalized_path(actual_path) == normalized_path(expected_path),
        "moduleSizeMatch": actual_size == expected_size,
    }
    if not facts["modulePathMatch"] or not facts["moduleSizeMatch"]:
        raise RuntimeError(
            "attached GameAssembly does not match the hash-verified module: "
            f"pathMatch={facts['modulePathMatch']}, sizeMatch={facts['moduleSizeMatch']}"
        )
    return facts


def read_jsonl(
    paths: Iterable[Path],
    *,
    label: str,
    normalize: Callable[[dict[str, Any], str], dict[str, Any]],
    validation_error: type[ValueError],
) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    sources: list[str] = []
    for path in paths:
        resolved = path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"{label} runtime trace not found: {path}")
        try:
            display = resolved.relative_to(ROOT).as_posix()
        except ValueError:
            display = resolved.as_posix()
        sources.append(display)
        with resolved.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                source = f"{display}:{line_number}"
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise validation_error(f"{source}: invalid JSON: {exc.msg}") from exc
                if not isinstance(row, dict):
                    raise validation_error(f"{source}: each JSONL row must be an object")
                events.append(normalize(row, source))
    if not events:
        raise validation_error(f"{label} runtime trace contains no events")
    return events, sources


def write_report(
    output: Path,
    bundle: dict[str, Any],
    markdown: str,
    markdown_output: Path | None = None,
) -> Path:
    output = output.resolve()
    markdown_output = markdown_output.resolve() if markdown_output else output.with_suffix(".md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(markdown, encoding="utf-8", newline="\n")
    return markdown_output
