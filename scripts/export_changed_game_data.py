#!/usr/bin/env python3
"""Incrementally refresh locally exported VFS files without touching Updates.

The prepare phase compares authenticated VFS metadata against the last local
snapshot, stages only added/modified logical files, applies removals, and
writes a pending manifest.  The finalize phase advances the local snapshot
only after export.bat has completed every WebUI builder.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator

if __package__:
    from .common import ROOT, read_json
    from .export_full_from_game import (
        DEFAULT_ANIMESTUDIO,
        DEFAULT_GAME_ROOT,
        DEFAULT_OUTPUT,
        DEFAULT_REPORTS,
        FOCUSED_STRUCTURED_BLOCK_TYPES,
        SOURCE_FINGERPRINT_EXCLUDED_TOP_LEVEL,
        SOURCES,
        TERRAIN_HEIGHT_FILE_REGEX,
        collect_source_sizes,
    )
else:
    from common import ROOT, read_json
    from export_full_from_game import (
        DEFAULT_ANIMESTUDIO,
        DEFAULT_GAME_ROOT,
        DEFAULT_OUTPUT,
        DEFAULT_REPORTS,
        FOCUSED_STRUCTURED_BLOCK_TYPES,
        SOURCE_FINGERPRINT_EXCLUDED_TOP_LEVEL,
        SOURCES,
        TERRAIN_HEIGHT_FILE_REGEX,
        collect_source_sizes,
    )


SCHEMA_VERSION = 1
DEFAULT_AUDIT_LEDGER = ROOT / "reports" / "animestudio" / "vfs_understanding_files_latest.jsonl.gz"
DEFAULT_AUDIT_SUMMARY = ROOT / "reports" / "animestudio" / "vfs_understanding_latest.json"
DEFAULT_EXPORT_SUMMARY = DEFAULT_REPORTS / "export_full_summary.json"
DEFAULT_REPORT = DEFAULT_REPORTS / "local_changed_export_latest.json"
LOCAL_STATE_REL = Path("recovered/AnimeStudio-cli/local_incremental")
MAX_REGEX_CHARS = 6000


class ChangedExportError(RuntimeError):
    pass


@contextmanager
def _exclusive_lock(output_root: Path) -> Iterator[None]:
    state_root = output_root / LOCAL_STATE_REL
    state_root.mkdir(parents=True, exist_ok=True)
    lock = state_root / "workflow.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ChangedExportError(f"another local changed-only export is active, or left a stale lock: {lock}") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        lock.unlink(missing_ok=True)


def _slash(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(raw)
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_snapshot(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(raw)
    try:
        with temporary.open("wb") as output:
            with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
                compressed.write((json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_snapshot(path: Path) -> dict[str, Any]:
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise ChangedExportError(f"invalid local incremental snapshot {path}: {exc}") from exc
    if payload.get("schemaVersion") != SCHEMA_VERSION or not isinstance(payload.get("files"), list):
        raise ChangedExportError(f"unsupported local incremental snapshot: {path}")
    return payload


def structured_steps(mode: str) -> list[dict[str, Any]]:
    if mode not in {"focused", "default"}:
        raise ChangedExportError("--changed-only supports focused or default structured mode, not debug")
    steps = [{"name": "required", "blocks": tuple(FOCUSED_STRUCTURED_BLOCK_TYPES), "regexes": ()}]
    if mode == "default":
        steps.append({"name": "terrain_height", "blocks": ("terrain",), "regexes": (TERRAIN_HEIGHT_FILE_REGEX,)})
    return steps


def _run(command: list[str], *, cwd: Path = ROOT) -> None:
    try:
        subprocess.run(command, cwd=cwd, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ChangedExportError(f"command failed: {command[0]} ({exc})") from exc


def _load_index_rows(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    files: list[dict[str, Any]] = []
    summary: dict[str, Any] | None = None
    seen: set[str] = set()
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                record_type = row.get("recordType")
                if record_type == "file":
                    logical_id = str(row.get("logicalId") or "")
                    if not logical_id or logical_id in seen:
                        raise ChangedExportError(f"duplicate/empty logicalId at {path}:{line_number}: {logical_id!r}")
                    seen.add(logical_id)
                    files.append({
                        "logicalId": logical_id,
                        "blockName": str(row.get("blockName") or ""),
                        "blockTypeValue": int(row.get("fileBlockTypeValue")),
                        "virtualPath": str(row.get("fileName") or ""),
                        "fileDataMd5DisplayHex": str(row.get("fileDataMd5") or "").upper(),
                        "length": int(row.get("length")),
                        "encrypted": bool(row.get("encrypted")),
                    })
                elif record_type == "summary":
                    summary = row
    except ChangedExportError:
        raise
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ChangedExportError(f"invalid VFS index {path}: {exc}") from exc
    if summary is None:
        raise ChangedExportError(f"VFS index has no terminal summary: {path}")
    if int(summary.get("missingChunkCount") or 0) != 0:
        raise ChangedExportError(f"VFS index contains missing chunks: {path}")
    if int(summary.get("fileCount") or 0) != len(files):
        raise ChangedExportError(
            f"VFS index count mismatch for {path}: expected={summary.get('fileCount')}, actual={len(files)}"
        )
    return files, summary


def scan_source(
    *, executable: Path, game_root: Path, source: str, mode: str, work: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    primary = game_root / source
    fallback_name = "Persistent" if source == "StreamingAssets" else "StreamingAssets"
    fallback = game_root / fallback_name
    combined: dict[str, dict[str, Any]] = {}
    summaries: list[dict[str, Any]] = []
    for index, step in enumerate(structured_steps(mode)):
        output = work / f"{source}-{index}-{step['name']}.jsonl"
        command = [str(executable), "vfs-index", "--jsonl", "-s", str(primary), "-o", str(output)]
        if fallback.is_dir():
            command.extend(["--fallback-assets", str(fallback)])
        for block in step["blocks"]:
            command.extend(["--block-type", str(block)])
        for pattern in step["regexes"]:
            command.extend(["--file-regex", str(pattern)])
        _run(command)
        rows, summary = _load_index_rows(output)
        summaries.append(summary)
        for row in rows:
            logical_id = row["logicalId"]
            if logical_id in combined:
                raise ChangedExportError(f"logical file appears in multiple structured steps: {logical_id}")
            combined[logical_id] = row
    return [combined[key] for key in sorted(combined)], summaries


def _file_map(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        logical_id = str(row["logicalId"])
        if logical_id in result:
            raise ChangedExportError(f"duplicate baseline logicalId: {logical_id}")
        result[logical_id] = row
    return result


def classify_changes(
    previous: Iterable[dict[str, Any]], current: Iterable[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    old = _file_map(previous)
    new = _file_map(current)
    added = [new[key] for key in sorted(new.keys() - old.keys())]
    deleted = [old[key] for key in sorted(old.keys() - new.keys())]
    modified: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    identity_fields = ("blockTypeValue", "virtualPath", "fileDataMd5DisplayHex", "length", "encrypted")
    for key in sorted(old.keys() & new.keys()):
        target = modified if any(old[key].get(field) != new[key].get(field) for field in identity_fields) else unchanged
        target.append(new[key])
    return {"added": added, "modified": modified, "deleted": deleted, "unchanged": unchanged}


def _audit_seed_rows(path: Path, mode: str) -> tuple[list[dict[str, Any]], str]:
    allowed_blocks = {"Table", "JsonData", "Video", "AuditVideo"}
    terrain_re = re.compile(TERRAIN_HEIGHT_FILE_REGEX) if mode == "default" else None
    rows: dict[str, dict[str, Any]] = {}
    input_set = ""
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if row.get("recordType") != "file" or row.get("boundaryStatus") != "boundary_verified":
                    continue
                block = str(row.get("blockName") or "")
                virtual_path = str(row.get("virtualPath") or "")
                if block == "Terrain" and terrain_re is not None and terrain_re.fullmatch(virtual_path):
                    pass
                elif block not in allowed_blocks:
                    continue
                logical_id = f"{block}/{virtual_path.lstrip('/')}"
                if logical_id in rows:
                    raise ChangedExportError(f"duplicate logical file in audit seed: {logical_id}")
                input_set = input_set or str(row.get("inputSetSha256") or "")
                if input_set != str(row.get("inputSetSha256") or ""):
                    raise ChangedExportError("audit seed mixes input-set fingerprints")
                rows[logical_id] = {
                    "logicalId": logical_id,
                    "blockName": block,
                    "blockTypeValue": int(row.get("blockTypeValue")),
                    "virtualPath": virtual_path,
                    "fileDataMd5DisplayHex": str(row.get("declaredFileDataMd5DisplayHex") or "").upper(),
                    "length": int(row.get("length")),
                    "encrypted": bool(row.get("encrypted")),
                }
    except ChangedExportError:
        raise
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ChangedExportError(f"invalid audit seed {path}: {exc}") from exc
    if not rows or not input_set:
        raise ChangedExportError(f"audit seed contains no usable verified files: {path}")
    return [rows[key] for key in sorted(rows)], input_set


def validate_audit_seed_summary(
    path: Path,
    *,
    ledger_input_set: str,
    game_root: Path,
    previous_source: dict[str, Any],
) -> None:
    """Bind the certified Persistent ledger to the export being refreshed.

    The audit inventories every old VFS metadata/chunk file. Files outside VFS
    are small launcher/config companions; their current count binds the audit
    to the previous source file count, while the previous byte total must still
    contain every certified VFS byte. Companion files may change independently
    during the same client patch, so their old byte total cannot be inferred
    from the current copies.
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChangedExportError(f"invalid audit summary {path}: {exc}") from exc
    if payload.get("inputSetSha256") != ledger_input_set:
        raise ChangedExportError("audit summary and ledger input-set fingerprints differ")
    expected_primary = (game_root / "Persistent").resolve()
    actual_primary = Path(str(payload.get("primaryAssets") or "")).resolve()
    if os.path.normcase(str(actual_primary)) != os.path.normcase(str(expected_primary)):
        raise ChangedExportError(
            f"audit primary root mismatch: expected={expected_primary}, actual={actual_primary}"
        )
    inventory: dict[str, int] = {}
    for collection in (payload.get("sourceFingerprints"), payload.get("physicalChunkInventory")):
        if not isinstance(collection, list):
            raise ChangedExportError(f"audit summary has no complete VFS inventory: {path}")
        for row in collection:
            if not isinstance(row, dict) or row.get("role") != "primary":
                continue
            item_path = os.path.normcase(str(Path(str(row.get("path") or "")).resolve()))
            if not item_path or item_path in inventory:
                raise ChangedExportError(f"duplicate/empty primary VFS inventory path in {path}: {item_path!r}")
            inventory[item_path] = int(row.get("length"))
    if not inventory:
        raise ChangedExportError(f"audit summary has no primary VFS inventory: {path}")

    non_vfs_files = 0
    excluded = SOURCE_FINGERPRINT_EXCLUDED_TOP_LEVEL.get("Persistent", frozenset())
    for item in expected_primary.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(expected_primary)
        if relative.parts and (relative.parts[0] in excluded or relative.parts[0].lower() == "vfs"):
            continue
        non_vfs_files += 1
    reconstructed_files = len(inventory) + non_vfs_files
    certified_vfs_bytes = sum(inventory.values())
    expected = {key: int(previous_source.get(key) or -1) for key in ("files", "bytes")}
    if expected["files"] != reconstructed_files or expected["bytes"] < certified_vfs_bytes:
        raise ChangedExportError(
            "certified audit does not describe the previous exported Persistent source: "
            f"expected={expected}, reconstructedFiles={reconstructed_files}, "
            f"certifiedVfsBytes={certified_vfs_bytes}"
        )


def output_relative_path(row: dict[str, Any]) -> PurePosixPath:
    block = str(row["blockName"])
    raw_virtual_path = str(row["virtualPath"]).replace("\\", "/")
    if raw_virtual_path.startswith("/") or re.match(r"^[A-Za-z]:", raw_virtual_path):
        raise ChangedExportError(f"unsafe logical output path: {raw_virtual_path}")
    virtual_path = raw_virtual_path
    source = PurePosixPath(virtual_path)
    if not virtual_path or ".." in source.parts or source.is_absolute():
        raise ChangedExportError(f"unsafe logical output path: {virtual_path}")
    if block == "Table":
        return PurePosixPath("Table") / f"{source.stem}.json"
    if block == "Lua":
        name = virtual_path
        if not name.endswith(".lua"):
            suffix = ".lua.enc"
            while name.endswith(suffix):
                name = name[: -len(suffix)]
            name += ".lua"
        return PurePosixPath("Lua") / name
    if block in {"Video", "AuditVideo"} and virtual_path.endswith(".usm"):
        return PurePosixPath(virtual_path[:-4] + ".mp4")
    return source


def _regex_batches(rows: list[dict[str, Any]]) -> list[str]:
    batches: list[str] = []
    current: list[str] = []
    current_length = 5
    for row in rows:
        item = re.escape(str(row["virtualPath"]).replace("\\", "/"))
        added = len(item) + (1 if current else 0)
        if current and current_length + added > MAX_REGEX_CHARS:
            batches.append(r"^(?:" + "|".join(current) + r")$")
            current = []
            current_length = 5
        current.append(item)
        current_length += added
    if current:
        batches.append(r"^(?:" + "|".join(current) + r")$")
    return batches


def stage_changed_files(
    *, executable: Path, game_root: Path, source: str, rows: list[dict[str, Any]], stage: Path
) -> dict[PurePosixPath, Path]:
    primary = game_root / source
    fallback_name = "Persistent" if source == "StreamingAssets" else "StreamingAssets"
    fallback = game_root / fallback_name
    by_block: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_block.setdefault(str(row["blockName"]), []).append(row)
    for block, block_rows in sorted(by_block.items()):
        for pattern in _regex_batches(block_rows):
            command = [
                str(executable), "dump", "-s", str(primary), "-o", str(stage),
                "--block-type", block, "--file-regex", pattern, "--verify-md5",
            ]
            if fallback.is_dir():
                command.extend(["--fallback-assets", str(fallback)])
            _run(command)
    expected: dict[PurePosixPath, Path] = {}
    for row in rows:
        relative = output_relative_path(row)
        staged = stage.joinpath(*relative.parts)
        if relative in expected:
            raise ChangedExportError(f"multiple changed logical files map to {relative}")
        if not staged.is_file():
            raise ChangedExportError(f"changed logical file produced no expected output: {row['logicalId']} -> {relative}")
        expected[relative] = staged
    actual = {
        PurePosixPath(item.relative_to(stage).as_posix())
        for item in stage.rglob("*")
        if item.is_file()
    }
    if actual != set(expected):
        extra = sorted(str(item) for item in actual - set(expected))[:8]
        missing = sorted(str(item) for item in set(expected) - actual)[:8]
        raise ChangedExportError(f"staged output mismatch: extra={extra}, missing={missing}")
    return expected


def publish_transaction(
    *, output_root: Path, source: str, staged: dict[PurePosixPath, Path], deleted: list[dict[str, Any]], backup: Path
) -> None:
    destination_root = (output_root / "structured" / source).resolve()
    destination_root.mkdir(parents=True, exist_ok=True)
    actions: dict[PurePosixPath, Path | None] = dict(staged)
    for row in deleted:
        relative = output_relative_path(row)
        if relative in actions:
            raise ChangedExportError(f"delete/write collision for structured output {relative}")
        actions[relative] = None
    moved_backups: list[tuple[Path, Path]] = []
    published: list[Path] = []
    try:
        for relative, staged_path in sorted(actions.items(), key=lambda item: str(item[0])):
            destination = destination_root.joinpath(*relative.parts).resolve()
            try:
                destination.relative_to(destination_root)
            except ValueError as exc:
                raise ChangedExportError(f"structured destination escapes output root: {destination}") from exc
            # A previous failed wrapper run may already have applied this
            # deletion while deliberately leaving the baseline unadvanced.
            # Treat that state as retryable; the old snapshot still proves
            # that this path is the deletion target.
            if staged_path is None and not destination.is_file():
                continue
            if destination.exists():
                backup_path = backup.joinpath(*relative.parts)
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(destination, backup_path)
                moved_backups.append((backup_path, destination))
            if staged_path is not None:
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged_path, destination)
                published.append(destination)
    except Exception:
        for destination in reversed(published):
            destination.unlink(missing_ok=True)
        for backup_path, destination in reversed(moved_backups):
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(backup_path, destination)
        raise


def _snapshot_path(output_root: Path, source: str) -> Path:
    return output_root / LOCAL_STATE_REL / f"{source.lower()}_structured_vfs.json.gz"


def _pending_snapshot_path(output_root: Path, source: str) -> Path:
    return output_root / LOCAL_STATE_REL / f"pending_{source.lower()}_structured_vfs.json.gz"


def _fingerprint_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(left.get(key) == right.get(key) for key in ("files", "bytes", "fingerprint", "latest_mtime_ns"))


def can_retry_applied_abort(
    manifest: dict[str, Any],
    *,
    game_root: Path,
    output_root: Path,
    mode: str,
    current_sizes: dict[str, dict[str, Any]],
) -> bool:
    """Accept only an exact retry of files published by a completed prepare."""

    if not (
        manifest.get("schemaVersion") == SCHEMA_VERSION
        and manifest.get("complete") is True
        and manifest.get("aborted") is True
        and manifest.get("structuredFilesApplied") is True
        and manifest.get("structuredDumpMode") == mode
    ):
        return False
    try:
        manifest_game_root = Path(str(manifest["gameRoot"])).resolve()
        manifest_output_root = Path(str(manifest["outputRoot"])).resolve()
    except (KeyError, TypeError, OSError):
        return False
    if os.path.normcase(str(manifest_game_root)) != os.path.normcase(str(game_root)):
        return False
    if os.path.normcase(str(manifest_output_root)) != os.path.normcase(str(output_root)):
        return False
    manifest_sizes = manifest.get("sourceFingerprints") or {}
    return all(_fingerprint_equal(manifest_sizes.get(source) or {}, current_sizes[source]) for source in SOURCES)


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    game_root = args.game_root.resolve()
    output_root = args.output.resolve()
    executable = args.animestudio.resolve()
    previous_summary = read_json(args.export_summary, {})
    if not game_root.is_dir() or not output_root.is_dir():
        raise ChangedExportError(f"game/export root missing: game={game_root}, output={output_root}")
    if not executable.is_file():
        raise ChangedExportError(f"AnimeStudio CLI not found: {executable}")
    previous_game_root = Path(str(previous_summary.get("game_root") or "")).resolve()
    previous_output_root = Path(str(previous_summary.get("output_root") or "")).resolve()
    if os.path.normcase(str(previous_game_root)) != os.path.normcase(str(game_root)):
        raise ChangedExportError(
            f"previous export summary game root mismatch: expected={game_root}, actual={previous_game_root}"
        )
    if os.path.normcase(str(previous_output_root)) != os.path.normcase(str(output_root)):
        raise ChangedExportError(
            f"previous export summary output root mismatch: expected={output_root}, actual={previous_output_root}"
        )
    existing_manifest = read_json(args.manifest, {})
    if (
        existing_manifest.get("applied") is True
        and existing_manifest.get("baselineAdvanced") is not True
        and existing_manifest.get("aborted") is not True
    ):
        raise ChangedExportError(
            f"an earlier changed-only export is still pending: {args.manifest}; "
            "run the abort action before retrying"
        )
    previous_sizes = previous_summary.get("source_sizes") or {}
    current_sizes = collect_source_sizes(game_root, SOURCES)
    retry_applied_abort = can_retry_applied_abort(
        existing_manifest,
        game_root=game_root,
        output_root=output_root,
        mode=args.structured_dump_mode,
        current_sizes=current_sizes,
    )
    if not previous_sizes:
        raise ChangedExportError("previous export summary has no source_sizes; run one full export first")

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    work_parent = ROOT / "tmp" / "animestudio"
    work_parent.mkdir(parents=True, exist_ok=True)
    state_rows: list[dict[str, Any]] = []
    audit_seed: tuple[list[dict[str, Any]], str] | None = None
    with tempfile.TemporaryDirectory(prefix="changed-export-", dir=work_parent) as raw_work:
        work = Path(raw_work)
        prepared: list[tuple[str, dict[PurePosixPath, Path], list[dict[str, Any]], list[dict[str, Any]]]] = []
        for source in SOURCES:
            current_rows, scan_summaries = scan_source(
                executable=executable, game_root=game_root, source=source, mode=args.structured_dump_mode, work=work
            )
            baseline_path = _snapshot_path(output_root, source)
            baseline_kind = "local_snapshot"
            if retry_applied_abort:
                previous_rows = current_rows
                baseline_kind = "applied_aborted_retry"
            elif baseline_path.is_file():
                baseline = _read_snapshot(baseline_path)
                if baseline.get("structuredDumpMode") != args.structured_dump_mode:
                    raise ChangedExportError(
                        f"local snapshot mode mismatch for {source}: "
                        f"snapshot={baseline.get('structuredDumpMode')}, requested={args.structured_dump_mode}; "
                        "run a full export before changing structured dump modes"
                    )
                previous_rows = baseline["files"]
            elif _fingerprint_equal(previous_sizes.get(source) or {}, current_sizes[source]):
                previous_rows = current_rows
                baseline_kind = "unchanged_source_initialized"
            elif source == "Persistent" and args.audit_ledger.is_file():
                if audit_seed is None:
                    audit_seed = _audit_seed_rows(args.audit_ledger, args.structured_dump_mode)
                    validate_audit_seed_summary(
                        args.audit_summary,
                        ledger_input_set=audit_seed[1],
                        game_root=game_root,
                        previous_source=previous_sizes.get(source) or {},
                    )
                previous_rows = audit_seed[0]
                baseline_kind = "certified_outer_audit"
            else:
                raise ChangedExportError(
                    f"no trustworthy pre-update local snapshot for changed source {source}; run a full export once"
                )
            changes = classify_changes(previous_rows, current_rows)
            changed_rows = changes["added"] + changes["modified"]
            staged: dict[PurePosixPath, Path] = {}
            if changed_rows and not args.check:
                stage = work / "stage" / source
                stage.mkdir(parents=True, exist_ok=True)
                staged = stage_changed_files(
                    executable=executable, game_root=game_root, source=source, rows=changed_rows, stage=stage
                )
            prepared.append((source, staged, changes["deleted"], current_rows))
            change_ledger = {
                kind: [
                    {
                        key: row[key]
                        for key in (
                            "logicalId",
                            "blockName",
                            "blockTypeValue",
                            "virtualPath",
                            "fileDataMd5DisplayHex",
                            "length",
                            "encrypted",
                        )
                    }
                    for row in changes[kind]
                ]
                for kind in ("added", "modified", "deleted")
            }
            state_rows.append({
                "source": source,
                "baselineKind": baseline_kind,
                "previousFileCount": len(previous_rows),
                "currentFileCount": len(current_rows),
                "added": len(changes["added"]),
                "modified": len(changes["modified"]),
                "deleted": len(changes["deleted"]),
                "unchanged": len(changes["unchanged"]),
                "changedFiles": change_ledger,
                "scanSummaries": scan_summaries,
            })

        if not args.check:
            for source, staged, deleted, _current_rows in prepared:
                publish_transaction(
                    output_root=output_root, source=source, staged=staged, deleted=deleted, backup=work / "backup" / source
                )
            for source, _staged, _deleted, current_rows in prepared:
                _write_snapshot(_pending_snapshot_path(output_root, source), {
                    "schemaVersion": SCHEMA_VERSION,
                    "source": source,
                    "structuredDumpMode": args.structured_dump_mode,
                    "sourceFingerprint": current_sizes[source],
                    "files": current_rows,
                })

    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "mode": "check" if args.check else "prepare",
        "complete": True,
        "applied": not args.check,
        "structuredFilesApplied": not args.check,
        "updatesIntegration": "disabled",
        "gameRoot": str(game_root),
        "outputRoot": str(output_root),
        "structuredDumpMode": args.structured_dump_mode,
        "sourceFingerprints": current_sizes,
        "sources": state_rows,
        "pendingSnapshots": {
            source: _slash(_pending_snapshot_path(output_root, source)) for source in SOURCES
        },
        "auditSeedInputSetSha256": audit_seed[1] if audit_seed else None,
        "baselineAdvanced": False,
    }
    _write_json_atomic(args.report, payload)
    if not args.check:
        _write_json_atomic(args.manifest, payload)
    return payload


def finalize(args: argparse.Namespace) -> dict[str, Any]:
    manifest = read_json(args.manifest, {})
    if manifest.get("schemaVersion") != SCHEMA_VERSION or manifest.get("complete") is not True or manifest.get("applied") is not True:
        raise ChangedExportError(f"incremental manifest is not a completed prepare result: {args.manifest}")
    output_root = Path(manifest["outputRoot"]).resolve()
    for source in SOURCES:
        pending = _pending_snapshot_path(output_root, source)
        if not pending.is_file():
            raise ChangedExportError(f"pending local snapshot missing: {pending}")
    state_root = output_root / LOCAL_STATE_REL
    with tempfile.TemporaryDirectory(prefix="finalize-", dir=state_root) as raw_backup:
        backup_root = Path(raw_backup)
        replaced: list[tuple[Path, Path | None]] = []
        try:
            for source in SOURCES:
                baseline = _snapshot_path(output_root, source)
                baseline.parent.mkdir(parents=True, exist_ok=True)
                backup = backup_root / baseline.name if baseline.exists() else None
                if backup is not None:
                    os.replace(baseline, backup)
                replaced.append((baseline, backup))
                os.replace(_pending_snapshot_path(output_root, source), baseline)
        except Exception:
            for baseline, backup in reversed(replaced):
                baseline.unlink(missing_ok=True)
                if backup is not None and backup.exists():
                    os.replace(backup, baseline)
            raise
    manifest["mode"] = "finalized"
    manifest["baselineAdvanced"] = True
    manifest["aborted"] = False
    _write_json_atomic(args.report, manifest)
    _write_json_atomic(args.manifest, manifest)
    return manifest


def abort(args: argparse.Namespace) -> dict[str, Any]:
    manifest = read_json(args.manifest, {})
    if manifest.get("schemaVersion") != SCHEMA_VERSION:
        raise ChangedExportError(f"incremental manifest is unavailable or unsupported: {args.manifest}")
    if manifest.get("baselineAdvanced") is True:
        raise ChangedExportError("cannot abort a finalized changed-only export")
    try:
        output_root = Path(manifest["outputRoot"]).resolve()
    except (KeyError, TypeError) as exc:
        raise ChangedExportError(f"incremental manifest has no valid output root: {args.manifest}") from exc
    for source in SOURCES:
        _pending_snapshot_path(output_root, source).unlink(missing_ok=True)
    manifest["structuredFilesApplied"] = bool(
        manifest.get("structuredFilesApplied") is True or manifest.get("applied") is True
    )
    manifest["mode"] = "aborted"
    manifest["applied"] = False
    manifest["aborted"] = True
    _write_json_atomic(args.report, manifest)
    _write_json_atomic(args.manifest, manifest)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "finalize", "abort"))
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--animestudio", type=Path, default=DEFAULT_ANIMESTUDIO)
    parser.add_argument("--structured-dump-mode", choices=("focused", "default"), default="focused")
    parser.add_argument("--export-summary", type=Path, default=DEFAULT_EXPORT_SUMMARY)
    parser.add_argument("--audit-ledger", type=Path, default=DEFAULT_AUDIT_LEDGER)
    parser.add_argument("--audit-summary", type=Path, default=DEFAULT_AUDIT_SUMMARY)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_OUTPUT / LOCAL_STATE_REL / "pending_manifest.json")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.action != "prepare" and args.check:
        parser.error("--check is only valid with prepare")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.action == "prepare":
            output_root = args.output.resolve()
            operation = prepare
        else:
            preview = read_json(args.manifest, {})
            output_root = Path(preview.get("outputRoot") or args.output).resolve()
            operation = finalize if args.action == "finalize" else abort
        with _exclusive_lock(output_root):
            payload = operation(args)
    except ChangedExportError as exc:
        print(f"[changed-export] {exc}", file=sys.stderr)
        return 1
    totals = {
        key: sum(int(row.get(key) or 0) for row in payload.get("sources") or [])
        for key in ("added", "modified", "deleted", "unchanged")
    }
    print(f"[changed-export] {payload['mode']}: {totals}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
