#!/usr/bin/env python3
"""Track logical Endfield VFS data changes in compact SQLite snapshots.

The tracker consumes AnimeStudio ``vfs-index --jsonl`` records.  It can invoke
AnimeStudio for installed game data or import two JSONL files directly, which
keeps the snapshot and diff logic independently testable.

The baseline is deliberately immutable after initialization. Candidate
promotion remains disabled until a staged-export transaction can validate
output ownership and publish the Updates feed safely.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
from contextlib import closing
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence, TextIO


SCHEMA_VERSION = 1
PLAN_SCHEMA_VERSION = 1
JSONL_SCHEMA_VERSION = 1
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANIMESTUDIO = REPO_ROOT / Path(
    "tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe"
)
SOURCES = ("StreamingAssets", "Persistent")
JSONL_FORMAT = "animestudio-vfs-index"
JSONL_ENCODING = "jsonl"


class TrackerError(RuntimeError):
    """Expected, user-facing tracker failure."""


def _require_distinct_paths(**paths: Path) -> None:
    """Reject output aliases before any caller can mutate one of the paths."""
    resolved = {name: path.resolve() for name, path in paths.items()}
    names = list(resolved)
    for index, left_name in enumerate(names):
        left = resolved[left_name]
        for right_name in names[index + 1 :]:
            right = resolved[right_name]
            same = os.path.normcase(str(left)) == os.path.normcase(str(right))
            if not same and left.exists() and right.exists():
                try:
                    same = os.path.samefile(left, right)
                except OSError:
                    same = False
            if same:
                raise TrackerError(
                    f"{left_name} and {right_name} must be different paths: {left}"
                )


def normalize_logical_path(value: object) -> str:
    """Validate and return a stable, platform-independent VFS logical path.

    Slash direction is the sole accepted normalization.  Other aliases are
    rejected so two source names cannot silently collapse onto one logical ID.
    """
    original = str(value or "")
    if "\0" in original:
        raise TrackerError("logical filename contains a NUL byte")
    text = original.replace("\\", "/")
    normalized = unicodedata.normalize("NFC", text)
    if normalized != text:
        raise TrackerError("logical filename is not in canonical Unicode NFC form")
    if not normalized:
        raise TrackerError("file record has an empty logical filename")
    if normalized.startswith("/"):
        raise TrackerError(f"logical filename must not be rooted: {original!r}")
    if re.match(r"^[A-Za-z]:", normalized):
        raise TrackerError(f"logical filename must not be drive-qualified: {original!r}")
    segments = normalized.split("/")
    if any(segment == "" for segment in segments):
        raise TrackerError(f"logical filename contains an empty path segment: {original!r}")
    if any(segment in (".", "..") for segment in segments):
        raise TrackerError(f"logical filename contains a traversal alias: {original!r}")
    return normalized


def _first(record: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in record and record[name] is not None:
            return record[name]
    return default


def _record_type(record: Mapping[str, Any]) -> str:
    value = _first(record, "recordType", "record_type", "type", "kind", "record")
    return str(value or "").replace("_", "").replace("-", "").casefold()


def _text(value: object | None) -> str | None:
    return None if value is None else str(value)


def _integer(value: object | None, *, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TrackerError(f"expected an integer, got {value!r}") from exc


def _digest(value: object | None, *, required: bool = False) -> str | None:
    if value is None or str(value).strip() == "":
        if required:
            raise TrackerError("file record is missing its data MD5")
        return None
    result = str(value).strip().lower()
    if len(result) != 32 or any(ch not in "0123456789abcdef" for ch in result):
        raise TrackerError(f"invalid MD5 value: {value!r}")
    return result


def _canonical_source(value: str) -> str:
    folded = value.replace("_", "").replace("-", "").casefold()
    if folded == "streamingassets":
        return "StreamingAssets"
    if folded == "persistent":
        return "Persistent"
    raise TrackerError(f"unsupported VFS source: {value!r}")


def _open_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    try:
        stream: TextIO
        stream = path.open("r", encoding="utf-8-sig")
    except OSError as exc:
        raise TrackerError(f"cannot open JSONL input {path}: {exc}") from exc
    with stream:
        for line_number, raw_line in enumerate(stream, 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TrackerError(f"invalid JSON at {path}:{line_number}: {exc}") from exc
            if not isinstance(record, dict):
                raise TrackerError(f"expected an object at {path}:{line_number}")
            yield record


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=MEMORY;
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE TABLE blocks (
            source TEXT NOT NULL,
            block TEXT NOT NULL,
            version INTEGER,
            code_version INTEGER,
            hash_directory TEXT,
            PRIMARY KEY (source, block)
        ) WITHOUT ROWID;
        CREATE TABLE chunks (
            source TEXT NOT NULL,
            block TEXT NOT NULL,
            name TEXT NOT NULL,
            content_md5 TEXT,
            length INTEGER,
            physical_source TEXT,
            relative_path TEXT,
            PRIMARY KEY (source, block, name)
        ) WITHOUT ROWID;
        CREATE TABLE files (
            source TEXT NOT NULL,
            block TEXT NOT NULL,
            logical_path TEXT NOT NULL,
            data_md5 TEXT NOT NULL,
            length INTEGER NOT NULL,
            chunk_name TEXT,
            chunk_content_md5 TEXT,
            chunk_source TEXT,
            name_hash TEXT,
            PRIMARY KEY (source, block, logical_path)
        ) WITHOUT ROWID;
        CREATE TABLE missing_blocks (
            source TEXT NOT NULL,
            block TEXT NOT NULL,
            hash_directory TEXT,
            PRIMARY KEY (source, block)
        ) WITHOUT ROWID;
        """
    )


def _insert_source_records(
    connection: sqlite3.Connection,
    source: str,
    records: Iterable[Mapping[str, Any]],
) -> None:
    source = _canonical_source(source)
    current_block: str | None = None
    current_chunk: dict[str, Any] = {}
    record_counts: dict[str, int] = {}
    header_count = 0
    summary_count = 0
    file_record_count = 0
    missing_block_count = 0
    saw_summary = False

    for record in records:
        kind = _record_type(record)
        record_counts[kind or "unknown"] = record_counts.get(kind or "unknown", 0) + 1
        if saw_summary:
            raise TrackerError(f"{source} JSONL summary must be the terminal record")
        if kind == "header":
            header_count += 1
            if sum(record_counts.values()) != 1:
                raise TrackerError(f"{source} JSONL header must be the first record")
            schema_version = _integer(_first(record, "schemaVersion", "schema_version"))
            if schema_version != JSONL_SCHEMA_VERSION:
                raise TrackerError(
                    f"unsupported {source} JSONL schema version: {schema_version!r}"
                )
            if record.get("format") != JSONL_FORMAT or record.get("encoding") != JSONL_ENCODING:
                raise TrackerError(
                    f"unsupported {source} JSONL header format or encoding"
                )
            continue
        if header_count != 1:
            raise TrackerError(f"{source} JSONL must start with exactly one header")
        if kind == "block":
            current_block = str(_first(record, "block", "blockType", "name"))
            connection.execute(
                "INSERT OR REPLACE INTO blocks VALUES (?, ?, ?, ?, ?)",
                (
                    source,
                    current_block,
                    _integer(_first(record, "version", "vfsVersion")),
                    _integer(_first(record, "codeVersion", "code_version")),
                    _text(_first(record, "hashDirectory", "hash_directory")),
                ),
            )
            current_chunk = {}
            continue
        if kind == "chunk":
            block = str(_first(record, "block", "blockType", "blockName", default=current_block))
            if not block or block == "None":
                raise TrackerError(f"{source} chunk record is missing its block")
            name = str(_first(record, "name", "fileName", "chunkFile", "chunkName"))
            if not name or name == "None":
                raise TrackerError(f"{source}/{block} chunk record is missing its name")
            if _first(record, "exists", "chunkExists", default=True) is False:
                raise TrackerError(f"{source}/{block} is missing chunk {name}")
            current_block = block
            current_chunk = {
                "name": name,
                "content_md5": _digest(_first(record, "contentMd5", "chunkContentMd5")),
                "source": _text(_first(record, "source", "chunkSource")),
            }
            connection.execute(
                "INSERT OR REPLACE INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    source,
                    block,
                    name,
                    current_chunk["content_md5"],
                    _integer(_first(record, "length", "chunkLength")),
                    current_chunk["source"],
                    _text(_first(record, "relativePath", "chunkRelativePath")),
                ),
            )
            continue
        if kind == "file":
            block = str(
                _first(
                    record,
                    "blockName",
                    "block",
                    "blockType",
                    "fileBlockType",
                    default=current_block,
                )
            )
            if not block or block == "None":
                raise TrackerError(f"{source} file record is missing its block")
            logical_path = normalize_logical_path(
                _first(record, "logicalPath", "fileName", "name", "path")
            )
            logical_id = _text(record.get("logicalId"))
            if logical_id is not None and logical_id != f"{block}/{logical_path}":
                raise TrackerError(
                    f"{source}/{block}/{logical_path} has an inconsistent logicalId"
                )
            length = _integer(_first(record, "length", "fileLength"))
            if length is None or length < 0:
                raise TrackerError(f"{source}/{block}/{logical_path} has invalid length")
            chunk_name = _text(
                _first(record, "chunkName", "chunkFile", "chunkFileName", default=current_chunk.get("name"))
            )
            chunk_md5 = _digest(
                _first(
                    record,
                    "chunkContentMd5",
                    "contentMd5",
                    default=current_chunk.get("content_md5"),
                )
            )
            chunk_source = _text(
                _first(record, "chunkSource", "physicalSource", default=current_chunk.get("source"))
            )
            values = (
                source,
                block,
                logical_path,
                _digest(_first(record, "dataMd5", "fileDataMd5"), required=True),
                length,
                chunk_name,
                chunk_md5,
                chunk_source,
                _text(_first(record, "nameHash", "fileNameHash")),
            )
            try:
                connection.execute("INSERT INTO files VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
            except sqlite3.IntegrityError as exc:
                raise TrackerError(
                    f"duplicate logical file: {source}/{block}/{logical_path}"
                ) from exc
            file_record_count += 1
            continue
        if kind == "missingblock":
            block = str(_first(record, "block", "blockType", "name"))
            if not block or block == "None":
                raise TrackerError(f"{source} missingBlock record is missing its block")
            connection.execute(
                "INSERT OR REPLACE INTO missing_blocks VALUES (?, ?, ?)",
                (source, block, _text(_first(record, "hashDirectory", "hash_directory"))),
            )
            missing_block_count += 1
            continue
        if kind == "summary":
            summary_count += 1
            declared_files = _integer(_first(record, "fileCount", "file_count"))
            if declared_files is None or declared_files != file_record_count:
                raise TrackerError(
                    f"{source} summary fileCount {declared_files!r} does not match "
                    f"{file_record_count} file records"
                )
            declared_missing_blocks = _integer(
                _first(record, "missingBlockCount", "missing_block_count")
            )
            if (
                declared_missing_blocks is not None
                and declared_missing_blocks != missing_block_count
            ):
                raise TrackerError(
                    f"{source} summary missingBlockCount {declared_missing_blocks} does not "
                    f"match {missing_block_count} records"
                )
            missing_chunks = _integer(
                _first(record, "missingChunkCount", "missing_chunk_count"), default=0
            )
            if missing_chunks:
                raise TrackerError(f"{source} scan reports {missing_chunks} missing chunks")
            saw_summary = True
            continue
        raise TrackerError(f"unsupported {source} JSONL record type: {kind or '<missing>'}")

    if header_count != 1 or summary_count != 1 or not saw_summary:
        raise TrackerError(
            f"{source} JSONL requires exactly one header and one terminal summary"
        )
    connection.execute(
        "INSERT INTO metadata VALUES (?, ?)",
        (f"record_counts.{source}", json.dumps(record_counts, sort_keys=True, separators=(",", ":"))),
    )


def _snapshot_id(connection: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    for row in connection.execute(
        "SELECT source, block, logical_path, data_md5, length FROM files "
        "ORDER BY source, block, logical_path"
    ):
        digest.update(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _atomic_target(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    return Path(name)


def build_snapshot(
    destination: Path,
    streaming_jsonl: Path,
    persistent_jsonl: Path,
    *,
    replace: bool = False,
) -> dict[str, Any]:
    """Stream two JSONL indexes into an atomic SQLite snapshot."""
    destination = destination.resolve()
    if destination.exists() and not replace:
        raise TrackerError(f"refusing to overwrite existing snapshot: {destination}")
    temporary = _atomic_target(destination)
    try:
        with closing(sqlite3.connect(temporary)) as connection:
            _create_schema(connection)
            with closing(_open_jsonl(streaming_jsonl)) as records:
                _insert_source_records(connection, "StreamingAssets", records)
            with closing(_open_jsonl(persistent_jsonl)) as records:
                _insert_source_records(connection, "Persistent", records)
            snapshot_id = _snapshot_id(connection)
            file_count = connection.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            connection.executemany(
                "INSERT INTO metadata VALUES (?, ?)",
                (
                    ("schema_version", str(SCHEMA_VERSION)),
                    ("snapshot_id", snapshot_id),
                    ("file_count", str(file_count)),
                ),
            )
            connection.commit()
        with temporary.open("rb+") as stream:
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, destination)
        else:
            try:
                os.link(temporary, destination)
            except FileExistsError as exc:
                raise TrackerError(
                    f"refusing to overwrite snapshot created during scan: {destination}"
                ) from exc
            temporary.unlink()
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return {"path": str(destination), "snapshotId": snapshot_id, "fileCount": file_count}


def _invoke_animestudio(
    executable: Path,
    game_root: Path,
    temporary_root: Path,
) -> tuple[Path, Path]:
    streaming_assets = game_root / "StreamingAssets"
    persistent = game_root / "Persistent"
    if not streaming_assets.is_dir():
        raise TrackerError(f"StreamingAssets directory not found: {streaming_assets}")
    if not persistent.is_dir():
        raise TrackerError(f"Persistent directory not found: {persistent}")
    if not executable.is_file():
        raise TrackerError(f"AnimeStudio CLI not found: {executable}")
    try:
        help_probe = subprocess.run(
            [str(executable), "vfs-index", "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise TrackerError(f"cannot probe AnimeStudio vfs-index: {exc}") from exc
    help_text = (help_probe.stdout or "") + (help_probe.stderr or "")
    if "--jsonl" not in help_text:
        raise TrackerError(
            "AnimeStudio vfs-index does not support --jsonl; rebuild a CLI version "
            "with streaming index support or import JSONL fixtures explicitly"
        )
    before_fingerprint = _vfs_metadata_fingerprint(game_root)
    outputs = {
        "StreamingAssets": temporary_root / "streaming_assets.jsonl",
        "Persistent": temporary_root / "persistent.jsonl",
    }
    commands = (
        [
            str(executable),
            "vfs-index",
            "--jsonl",
            "--streaming-assets",
            str(streaming_assets),
            "--output",
            str(outputs["StreamingAssets"]),
        ],
        [
            str(executable),
            "vfs-index",
            "--jsonl",
            "--streaming-assets",
            str(persistent),
            "--fallback-assets",
            str(streaming_assets),
            "--output",
            str(outputs["Persistent"]),
        ],
    )
    for command in commands:
        try:
            subprocess.run(command, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise TrackerError(f"AnimeStudio vfs-index failed: {exc}") from exc
    after_fingerprint = _vfs_metadata_fingerprint(game_root)
    if after_fingerprint != before_fingerprint:
        raise TrackerError(
            "installed VFS metadata changed during the scan; discard the candidate "
            "and rerun after the game update finishes"
        )
    return outputs["StreamingAssets"], outputs["Persistent"]


def _vfs_metadata_fingerprint(game_root: Path) -> str:
    """Hash every VFS block catalog used to construct the logical-file index."""
    digest = hashlib.sha256()
    count = 0
    for source in SOURCES:
        root = game_root / source / "VFS"
        if not root.is_dir():
            raise TrackerError(f"VFS directory not found: {root}")
        try:
            paths = sorted(root.rglob("*.blc"), key=lambda path: path.as_posix().casefold())
        except OSError as exc:
            raise TrackerError(f"cannot enumerate VFS metadata under {root}: {exc}") from exc
        if not paths:
            raise TrackerError(f"no VFS block catalogs found under {root}")
        for path in paths:
            try:
                before = path.stat()
                relative = path.relative_to(game_root).as_posix()
                digest.update(relative.encode("utf-8"))
                digest.update(b"\0")
                digest.update(str(before.st_size).encode("ascii"))
                digest.update(b"\0")
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                after = path.stat()
            except OSError as exc:
                raise TrackerError(f"cannot fingerprint VFS metadata {path}: {exc}") from exc
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise TrackerError(f"VFS metadata changed while being read: {path}")
            digest.update(b"\n")
            count += 1
    digest.update(f"count={count}".encode("ascii"))
    return digest.hexdigest()


def _validate_snapshot(connection: sqlite3.Connection, path: Path) -> str:
    try:
        schema = connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        snapshot = connection.execute("SELECT value FROM metadata WHERE key='snapshot_id'").fetchone()
    except sqlite3.DatabaseError as exc:
        raise TrackerError(f"invalid snapshot database {path}: {exc}") from exc
    if schema is None or int(schema[0]) != SCHEMA_VERSION or snapshot is None:
        raise TrackerError(f"unsupported or incomplete snapshot database: {path}")
    return str(snapshot[0])


def _revisions(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {
            "source": source,
            "block": block,
            "version": version,
            "codeVersion": code_version,
        }
        for source, block, version, code_version in connection.execute(
            "SELECT source, block, version, code_version FROM blocks ORDER BY source, block"
        )
    ]


def _revision_map(connection: sqlite3.Connection) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (item["source"], item["block"]): {
            "version": item["version"],
            "codeVersion": item["codeVersion"],
        }
        for item in _revisions(connection)
    }


def _change_entry(
    status: str,
    key: tuple[str, str, str],
    old: Mapping[str, Any] | None,
    new: Mapping[str, Any] | None,
    old_revisions: Mapping[tuple[str, str], Mapping[str, Any]],
    new_revisions: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    source, block, logical_path = key
    return {
        "status": status,
        "source": source,
        "block": block,
        "logicalPath": logical_path,
        "oldDataMd5": old.get("dataMd5") if old else None,
        "newDataMd5": new.get("dataMd5") if new else None,
        "oldLength": old.get("length") if old else None,
        "newLength": new.get("length") if new else None,
        "oldChunk": (
            {
                "name": old.get("chunkName"),
                "contentMd5": old.get("chunkContentMd5"),
                "physicalSource": old.get("chunkSource"),
            }
            if old
            else None
        ),
        "newChunk": (
            {
                "name": new.get("chunkName"),
                "contentMd5": new.get("chunkContentMd5"),
                "physicalSource": new.get("chunkSource"),
            }
            if new
            else None
        ),
        "oldRevision": old_revisions.get((source, block)),
        "newRevision": new_revisions.get((source, block)),
    }


def compare_snapshots(
    baseline: Path,
    candidate: Path,
    *,
    sample_limit: int = 20,
    entry_limit: int = 5000,
) -> dict[str, Any]:
    if entry_limit < 0:
        raise TrackerError("entry limit must be non-negative")
    if sample_limit < 0:
        raise TrackerError("sample limit must be non-negative")
    with closing(sqlite3.connect(f"file:{baseline.resolve()}?mode=ro", uri=True)) as old_db:
        old_db.execute(
            "ATTACH DATABASE ? AS candidate",
            (f"file:{candidate.resolve()}?mode=ro",),
        )
        old_snapshot_id = _validate_snapshot(old_db, baseline)
        new_snapshot_row = old_db.execute(
            "SELECT value FROM candidate.metadata WHERE key='snapshot_id'"
        ).fetchone()
        new_schema_row = old_db.execute(
            "SELECT value FROM candidate.metadata WHERE key='schema_version'"
        ).fetchone()
        if (
            new_snapshot_row is None
            or new_schema_row is None
            or int(new_schema_row[0]) != SCHEMA_VERSION
        ):
            raise TrackerError(f"unsupported or incomplete snapshot database: {candidate}")
        new_snapshot_id = str(new_snapshot_row[0])
        old_revisions = _revision_map(old_db)
        new_revisions = {
            (source, block): {"version": version, "codeVersion": code_version}
            for source, block, version, code_version in old_db.execute(
                "SELECT source, block, version, code_version FROM candidate.blocks "
                "ORDER BY source, block"
            )
        }
        old_missing = set(old_db.execute("SELECT source, block FROM main.missing_blocks"))
        new_missing = set(old_db.execute("SELECT source, block FROM candidate.missing_blocks"))
        old_blocks = set(old_db.execute("SELECT source, block FROM main.blocks"))
        new_blocks = set(old_db.execute("SELECT source, block FROM candidate.blocks"))
        unexpected_missing = sorted((new_missing - old_missing) | (old_blocks - new_blocks))
        if unexpected_missing:
            sample = ", ".join(f"{source}/{block}" for source, block in unexpected_missing[:10])
            raise TrackerError(
                "candidate has previously present blocks reported missing; refusing a "
                f"potentially incomplete deletion diff: {sample}"
            )
        entries: list[dict[str, Any]] = []
        samples: list[dict[str, Any]] = []
        totals = {"added": 0, "modified": 0, "deleted": 0, "repacked": 0}
        retained_counts = {"added": 0, "modified": 0, "deleted": 0, "repacked": 0}
        query = """
            WITH keys AS (
                SELECT source, block, logical_path FROM main.files
                UNION
                SELECT source, block, logical_path FROM candidate.files
            )
            SELECT
                keys.source, keys.block, keys.logical_path,
                old.data_md5, old.length, old.chunk_name,
                old.chunk_content_md5, old.chunk_source,
                new.data_md5, new.length, new.chunk_name,
                new.chunk_content_md5, new.chunk_source
            FROM keys
            LEFT JOIN main.files AS old USING (source, block, logical_path)
            LEFT JOIN candidate.files AS new USING (source, block, logical_path)
            WHERE old.data_md5 IS NULL OR new.data_md5 IS NULL
               OR old.data_md5 != new.data_md5 OR old.length != new.length
               OR old.chunk_name IS NOT new.chunk_name
               OR old.chunk_content_md5 IS NOT new.chunk_content_md5
               OR old.chunk_source IS NOT new.chunk_source
            ORDER BY keys.source, keys.block, keys.logical_path
        """
        columns = (
            "dataMd5", "length", "chunkName", "chunkContentMd5", "chunkSource"
        )
        for row in old_db.execute(query):
            key = (row[0], row[1], row[2])
            old = dict(zip(columns, row[3:8])) if row[3] is not None else None
            new = dict(zip(columns, row[8:13])) if row[8] is not None else None
            status: str | None = None
            if old is None:
                status = "added"
            elif new is None:
                status = "deleted"
            elif (old["dataMd5"], old["length"]) != (new["dataMd5"], new["length"]):
                status = "modified"
            elif (
                old["chunkName"],
                old["chunkContentMd5"],
                old["chunkSource"],
            ) != (
                new["chunkName"],
                new["chunkContentMd5"],
                new["chunkSource"],
            ):
                status = "repacked"
            if status:
                totals[status] += 1
                if len(entries) < entry_limit or len(samples) < sample_limit:
                    entry = _change_entry(
                        status, key, old, new, old_revisions, new_revisions
                    )
                    if len(entries) < entry_limit:
                        entries.append(entry)
                        retained_counts[status] += 1
                    if len(samples) < sample_limit:
                        samples.append(entry)
        logical_changed = any(totals[name] for name in ("added", "modified", "deleted"))
        truncated_counts = {
            status: totals[status] - retained_counts[status] for status in totals
        }
        return {
            "schemaVersion": PLAN_SCHEMA_VERSION,
            "baseline": {"path": str(baseline.resolve()), "snapshotId": old_snapshot_id},
            "candidate": {"path": str(candidate.resolve()), "snapshotId": new_snapshot_id},
            "logicalChanged": logical_changed,
            "promotionRequired": logical_changed,
            "totals": totals,
            "entryLimit": entry_limit,
            "entriesTruncated": sum(truncated_counts.values()),
            "truncatedCounts": truncated_counts,
            "revisions": {
                "old": _revisions(old_db),
                "new": [
                    {
                        "source": source,
                        "block": block,
                        "version": revision["version"],
                        "codeVersion": revision["codeVersion"],
                    }
                    for (source, block), revision in sorted(new_revisions.items())
                ],
            },
            "entries": entries,
            "samples": samples,
        }


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path = path.resolve()
    temporary = _atomic_target(path)
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _add_input_arguments(parser: argparse.ArgumentParser) -> None:
    inputs = parser.add_argument_group("snapshot input")
    inputs.add_argument("--streaming-jsonl", type=Path, help="StreamingAssets vfs-index JSONL fixture")
    inputs.add_argument("--persistent-jsonl", type=Path, help="Persistent vfs-index JSONL fixture")
    inputs.add_argument("--game-root", type=Path, help="Endfield_Data containing StreamingAssets and Persistent")
    inputs.add_argument("--animestudio", type=Path, default=DEFAULT_ANIMESTUDIO)


def _resolve_inputs(args: argparse.Namespace, temporary_root: Path) -> tuple[Path, Path]:
    fixture_values = (args.streaming_jsonl, args.persistent_jsonl)
    if any(fixture_values):
        if not all(fixture_values) or args.game_root:
            raise TrackerError(
                "use both --streaming-jsonl and --persistent-jsonl, or use --game-root"
            )
        return args.streaming_jsonl, args.persistent_jsonl
    if not args.game_root:
        raise TrackerError(
            "snapshot input required: --game-root or both JSONL fixture arguments"
        )
    return _invoke_animestudio(args.animestudio.resolve(), args.game_root.resolve(), temporary_root)


def _build_from_args(destination: Path, args: argparse.Namespace, *, replace: bool) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="endfield-vfs-scan-") as temporary:
        streaming, persistent = _resolve_inputs(args, Path(temporary))
        return build_snapshot(destination, streaming, persistent, replace=replace)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    baseline = subparsers.add_parser(
        "baseline-current",
        help="build a baseline solely from the currently installed version",
    )
    baseline.add_argument("--baseline", type=Path, required=True)
    _add_input_arguments(baseline)

    snapshot = subparsers.add_parser("snapshot", help="build a standalone snapshot")
    snapshot.add_argument("--output", type=Path, required=True)
    snapshot.add_argument("--replace", action="store_true")
    _add_input_arguments(snapshot)

    check = subparsers.add_parser(
        "check",
        help="scan to a candidate and compare it without changing the baseline",
    )
    check.add_argument("--baseline", type=Path, required=True)
    check.add_argument("--candidate", type=Path, required=True)
    check.add_argument("--plan", type=Path, required=True)
    check.add_argument("--sample-limit", type=int, default=20)
    check.add_argument(
        "--entry-limit",
        type=int,
        default=5000,
        help="maximum detailed entries retained in the JSON plan [default: 5000]",
    )
    _add_input_arguments(check)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "baseline-current":
            result = _build_from_args(args.baseline, args, replace=False)
            result["mode"] = "baseline-current"
        elif args.command == "snapshot":
            result = _build_from_args(args.output, args, replace=args.replace)
            result["mode"] = "snapshot"
        elif args.command == "check":
            _require_distinct_paths(
                baseline=args.baseline,
                candidate=args.candidate,
                plan=args.plan,
            )
            if not args.baseline.is_file():
                raise TrackerError(f"baseline snapshot not found: {args.baseline}")
            # Candidates are explicitly disposable check outputs. Replacing them
            # by default makes repeated checks safe and ergonomic; baselines remain
            # immutable until a future staged-export transaction owns promotion.
            _build_from_args(args.candidate, args, replace=True)
            result = compare_snapshots(
                args.baseline,
                args.candidate,
                sample_limit=args.sample_limit,
                entry_limit=args.entry_limit,
            )
            _write_json_atomic(args.plan, result)
            result = {
                "mode": "check",
                "logicalChanged": result["logicalChanged"],
                "totals": result["totals"],
                "entriesTruncated": result["entriesTruncated"],
                "truncatedCounts": result["truncatedCounts"],
                "baselineSnapshotId": result["baseline"]["snapshotId"],
                "candidateSnapshotId": result["candidate"]["snapshotId"],
                "candidate": str(args.candidate.resolve()),
                "plan": str(args.plan.resolve()),
                "samples": result["samples"],
            }
        else:  # pragma: no cover - argparse enforces this
            raise AssertionError(args.command)
    except (TrackerError, OSError, sqlite3.DatabaseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
