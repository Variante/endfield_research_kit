"""Shared fail-closed file validation and JSONL helpers for saved runtime evidence."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable

from scripts.common import sha256_file
from scripts.repo_paths import REPO_ROOT


ROOT = REPO_ROOT


class CaptureConfigurationError(RuntimeError):
    """Raised when saved evidence does not match its selected build or manifest."""


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
                f"saved evidence mismatch: {name} size changed: expected {expected_size}, got {actual_size}"
            )
        actual_hash = sha256_file(path)
        if actual_hash.casefold() != expected_hash.casefold():
            raise CaptureConfigurationError(
                f"saved evidence mismatch: {name} SHA-256 changed: expected {expected_hash}, got {actual_hash}"
            )
        verified[name] = path
    return verified


def diagnostics_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.diagnostics.jsonl")


def normalized_path(value: str | Path) -> str:
    return str(Path(value).resolve()).replace("/", "\\").casefold()


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
