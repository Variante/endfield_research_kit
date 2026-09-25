"""Stateful export-tree change scanner behind the Updates feed.

Each run compares one export root with the snapshot cached in its state
directory and records every added, modified and deleted file. An export root
packs two families of small files into SQLite stores (layout v4):

* ``game/Unity.sqlite`` holds the Unity object documents; each row is
  expanded at its logical path ``game/Unity/<Type>/<name>``;
* ``game/GameFiles.sqlite`` holds every file under
  ``scripts.source_paths.PACKED_GAME_DIRS`` (``Json/LipSync``); each row is
  expanded at its own ``game/<path>``.

The scanner never fingerprints either database as one opaque file, and never
scans a store's SQLite sidecars. Each row becomes one virtual entry
fingerprinted by the row's stored SHA256 and size, so a broad audit reports
per-file changes exactly as it did for loose files. A row's bytes are read
from its store only when a loose file of the same name would have been read:
when the row is new or changed and has a text extension. A ``.json`` row that
holds binary MemoryPack (LipSync) is then classified by content like any loose
file: no reader owns it, so it is recorded as ``binary`` with no diff text.

A packed folder is read only from its store: loose files under a packed
folder are not game data in a v4 root and are never scanned.
"""
from __future__ import annotations

import concurrent.futures
import dataclasses
import datetime as dt
import difflib
import hashlib
import heapq
import json
import os
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Iterable, NamedTuple

from scripts.game_data.game_file_store import GameFileStore
from scripts.game_data.unity_store import STORE_FILE_NAME, UnityObjectStore, logical_ref
from scripts.source_paths import GAME_FILE_STORE_FILE, PACKED_GAME_DIRS, packed_game_dir
from scripts.webui.decoded_payloads import render_decoded_payload


TEXT_EXTENSIONS = {
    ".bat",
    ".cfg",
    ".conf",
    ".csv",
    ".ini",
    ".json",
    ".lua",
    ".md",
    ".rs",
    ".sql",
    ".toml",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

READ_CHUNK_SIZE = 1024 * 1024
PROGRESS_EVERY_FILES = 5000
TEXT_DIFF_MAX_BYTES = 256 * 1024
TEXT_DIFF_MAX_LINES = 240

# What the stored diffable text of a file is. A ``.json`` name means nothing
# about the bytes here: most of the export's Json tree is serialized, so the
# form is decided by the content and by whether a maintained reader owns it.
TEXT_KIND_PLAIN = "plain"            # the file's own UTF-8 text
TEXT_KIND_DECODED_WHOLE = "decoded_whole_file"  # a reader that read every byte
TEXT_KIND_DECODED_PARTIAL = "decoded_partial"   # a reader bounded to part of it
TEXT_KIND_BINARY = "binary"          # serialized, and no reader routes it
TEXT_KIND_TOO_LARGE = "binary_too_large"  # serialized, and over the diff limit
DEFAULT_HASH_WORKERS = max(2, min(8, (os.cpu_count() or 4)))
# The export's stores, relative to the export root, and the SQLite sidecars
# that may sit beside one while a writer has it open. Each store is expanded
# into per-row entries; neither a store nor a sidecar is ever scanned as a
# file of its own.
UNITY_STORE_RELATIVE_PATH = f"game/{STORE_FILE_NAME}"
UNITY_STORE_UNITY_PREFIX = "game/Unity"
GAME_FILE_STORE_RELATIVE_PATH = f"game/{GAME_FILE_STORE_FILE}"
EXPORT_STORE_RELATIVE_PATHS = (UNITY_STORE_RELATIVE_PATH, GAME_FILE_STORE_RELATIVE_PATH)
_STORE_SIDECAR_SUFFIXES = ("-journal", "-wal", "-shm")
# StoreRowRef.store values.
STORE_UNITY = "unity"
STORE_GAME_FILES = "game_files"


def _is_store_or_sidecar(rel_path: str, store_rel_path: str) -> bool:
    lower = normalize_relative_path(rel_path).lower()
    base = store_rel_path.lower()
    return lower == base or any(lower == base + suffix for suffix in _STORE_SIDECAR_SUFFIXES)


def is_unity_store_relative_path(rel_path: str) -> bool:
    """True for ``game/Unity.sqlite`` and its SQLite sidecars (any case)."""

    return _is_store_or_sidecar(rel_path, UNITY_STORE_RELATIVE_PATH)


def is_export_store_relative_path(rel_path: str) -> bool:
    """True for either export store (Unity.sqlite, GameFiles.sqlite) or a sidecar (any case)."""

    return any(_is_store_or_sidecar(rel_path, store) for store in EXPORT_STORE_RELATIVE_PATHS)


def is_packed_game_relative_path(rel_path: str) -> bool:
    """True for an export-root path at or under a packed game folder (any case)."""

    text = normalize_relative_path(rel_path).strip("/")
    if not text.lower().startswith("game/"):
        return False
    return packed_game_dir(text[len("game/"):]) is not None


class StoreRowRef(NamedTuple):
    """Where a virtual scan entry's bytes live: one row of one export store.

    For the Unity store ``type_name``/``name`` are the row's type and file
    name; for the game-file store they are the packed folder and the path
    inside it.
    """

    type_name: str
    name: str
    store: str = STORE_UNITY


class ExportFileEntry(NamedTuple):
    """One file to scan: a real file, or one store row at its logical path."""

    rel_path: str
    full_path: str
    size: int
    mtime_ns: int
    extension: str
    # Set for a store row: its stored SHA256 is the entry's digest, so the row
    # needs no read to be compared.
    store_row: StoreRowRef | None = None
    store_digest: str | None = None


@dataclasses.dataclass(slots=True)
class SnapshotRow:
    path: str
    size: int
    mtime_ns: int
    digest: str
    line_count: int | None
    extension: str
    text_content: str | None = None
    text_kind: str | None = None


@dataclasses.dataclass(slots=True)
class PendingFile:
    rel_path: str
    full_path: str
    size: int
    mtime_ns: int
    extension: str
    count_lines: bool
    capture_text: bool
    old_size: int | None
    old_digest: str | None
    old_line_count: int | None
    old_text_content: str | None
    old_text_kind: str | None = None
    store_row: StoreRowRef | None = None
    store_digest: str | None = None


@dataclasses.dataclass(slots=True)
class ScannedFile:
    rel_path: str
    size: int
    mtime_ns: int
    extension: str
    digest: str
    line_count: int | None
    text_content: str | None
    old_size: int | None
    old_digest: str | None
    old_line_count: int | None
    old_text_content: str | None
    text_kind: str | None = None
    old_text_kind: str | None = None


@dataclasses.dataclass(slots=True)
class ChangeEntry:
    path: str
    extension: str
    old_size: int | None = None
    new_size: int | None = None
    old_digest: str | None = None
    new_digest: str | None = None
    old_line_count: int | None = None
    new_line_count: int | None = None
    text_diff: list[str] | None = None
    text_diff_truncated: bool = False
    text_kind: str | None = None
    text_diff_note: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = {
            "path": self.path,
            "extension": self.extension,
            "old_size": self.old_size,
            "new_size": self.new_size,
            "old_digest": self.old_digest,
            "new_digest": self.new_digest,
            "old_line_count": self.old_line_count,
            "new_line_count": self.new_line_count,
        }
        if self.old_size is not None and self.new_size is not None:
            payload["size_delta"] = self.new_size - self.old_size
        if self.old_line_count is not None and self.new_line_count is not None:
            payload["line_delta"] = self.new_line_count - self.old_line_count
        if self.text_kind and self.text_kind != TEXT_KIND_PLAIN:
            payload["text_kind"] = self.text_kind
        if self.text_diff:
            payload["text_diff"] = self.text_diff
            if self.text_diff_truncated:
                payload["text_diff_truncated"] = True
        if self.text_diff_note:
            payload["text_diff_note"] = self.text_diff_note
        return payload


@dataclasses.dataclass(frozen=True, slots=True)
class ScanConfig:
    """Inputs for one stateful export-tree comparison."""

    root: Path
    state_dir: Path
    summary_json: Path
    summary_md: Path
    history_dir: Path | None = None
    workers: int = DEFAULT_HASH_WORKERS
    hash_batch_size: int = 1024
    sample_limit: int = 0
    top_line_limit: int = 25
    ignore_relative_paths: tuple[str, ...] = ()
    include_relative_paths: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class ScanResult:
    """Completed scan data and the two reports written for it."""

    payload: dict[str, object]
    summary_json: Path
    summary_md: Path


class ChangeAccumulator:
    def __init__(self, sample_limit: int, top_line_limit: int) -> None:
        self.sample_limit = sample_limit
        self.top_line_limit = top_line_limit

        self.scanned_files = 0
        self.reused_metadata_matches = 0
        self.metadata_only_updates = 0

        self.added_count = 0
        self.modified_count = 0
        self.deleted_count = 0

        self.added_by_extension: Counter[str] = Counter()
        self.modified_by_extension: Counter[str] = Counter()
        self.deleted_by_extension: Counter[str] = Counter()

        self.added_examples: list[ChangeEntry] = []
        self.modified_examples: list[ChangeEntry] = []
        self.deleted_examples: list[ChangeEntry] = []

        self._largest_line_changes: list[tuple[int, int, ChangeEntry]] = []
        self._line_order = 0

    def _remember_sample(self, bucket: list[ChangeEntry], entry: ChangeEntry) -> None:
        if self.sample_limit == 0 or len(bucket) < self.sample_limit:
            bucket.append(entry)

    def _remember_line_change(self, entry: ChangeEntry) -> None:
        if entry.old_line_count is None or entry.new_line_count is None:
            return
        magnitude = abs(entry.new_line_count - entry.old_line_count)
        if magnitude == 0:
            return
        token = (magnitude, self._line_order, entry)
        self._line_order += 1
        if len(self._largest_line_changes) < self.top_line_limit:
            heapq.heappush(self._largest_line_changes, token)
            return
        if token > self._largest_line_changes[0]:
            heapq.heapreplace(self._largest_line_changes, token)

    def note_scan(self) -> None:
        self.scanned_files += 1

    def note_reused_metadata_match(self) -> None:
        self.reused_metadata_matches += 1

    def note_metadata_only_update(self) -> None:
        self.metadata_only_updates += 1

    def record_added(self, scanned: ScannedFile) -> None:
        self.added_count += 1
        self.added_by_extension[display_extension(scanned.extension)] += 1
        text_diff, text_diff_truncated = build_text_diff(
            "",
            scanned.text_content,
            fromfile=f"a/{scanned.rel_path}",
            tofile=f"b/{scanned.rel_path}",
        )
        self._remember_sample(
            self.added_examples,
            ChangeEntry(
                path=scanned.rel_path,
                extension=scanned.extension,
                new_size=scanned.size,
                new_line_count=scanned.line_count,
                text_diff=text_diff,
                text_diff_truncated=text_diff_truncated,
                text_kind=scanned.text_kind,
            ),
        )

    def record_modified(self, scanned: ScannedFile) -> None:
        self.modified_count += 1
        self.modified_by_extension[display_extension(scanned.extension)] += 1
        text_diff, text_diff_truncated = build_text_diff(
            scanned.old_text_content,
            scanned.text_content,
            fromfile=f"a/{scanned.rel_path}",
            tofile=f"b/{scanned.rel_path}",
        )
        entry = ChangeEntry(
            path=scanned.rel_path,
            extension=scanned.extension,
            old_size=scanned.old_size,
            new_size=scanned.size,
            old_line_count=scanned.old_line_count,
            new_line_count=scanned.line_count,
            text_diff=text_diff,
            text_diff_truncated=text_diff_truncated,
            text_kind=scanned.text_kind,
            text_diff_note=modified_diff_note(scanned, text_diff),
        )
        self._remember_sample(self.modified_examples, entry)
        self._remember_line_change(entry)

    def record_deleted(
        self,
        rel_path: str,
        extension: str,
        old_size: int,
        old_line_count: int | None,
        old_text_content: str | None = None,
        old_text_kind: str | None = None,
    ) -> None:
        self.deleted_count += 1
        self.deleted_by_extension[display_extension(extension)] += 1
        text_diff, text_diff_truncated = build_text_diff(
            old_text_content,
            "",
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
        )
        self._remember_sample(
            self.deleted_examples,
            ChangeEntry(
                path=rel_path,
                extension=extension,
                old_size=old_size,
                old_line_count=old_line_count,
                text_diff=text_diff,
                text_diff_truncated=text_diff_truncated,
                text_kind=old_text_kind,
            ),
        )

    def top_line_changes(self) -> list[ChangeEntry]:
        ordered = sorted(self._largest_line_changes, key=lambda item: (-item[0], item[1]))
        return [entry for _, _, entry in ordered]

    def to_dict(self, started_at: dt.datetime, finished_at: dt.datetime) -> dict[str, object]:
        return {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
            "scanned_files": self.scanned_files,
            "changes": {
                "added": self.added_count,
                "modified": self.modified_count,
                "deleted": self.deleted_count,
                "metadata_only_updates": self.metadata_only_updates,
                "reused_metadata_matches": self.reused_metadata_matches,
            },
            "breakdown": {
                "added_by_extension": dict(self.added_by_extension.most_common()),
                "modified_by_extension": dict(self.modified_by_extension.most_common()),
                "deleted_by_extension": dict(self.deleted_by_extension.most_common()),
            },
            "samples": {
                "added": [entry.to_dict() for entry in self.added_examples],
                "modified": [entry.to_dict() for entry in self.modified_examples],
                "deleted": [entry.to_dict() for entry in self.deleted_examples],
                "largest_line_changes": [entry.to_dict() for entry in self.top_line_changes()],
            },
        }


def display_extension(extension: str) -> str:
    return extension or "[no extension]"


def normalize_relative_path(path: str) -> str:
    return path.replace("\\", "/")


def normalize_cli_relative_path(path: str) -> str:
    return normalize_relative_path(path.strip().strip("/"))


def try_relative_to(path: Path, root: Path) -> str | None:
    try:
        return normalize_relative_path(str(path.resolve().relative_to(root.resolve())))
    except ValueError:
        return None


def is_text_extension(extension: str) -> bool:
    return extension.lower() in TEXT_EXTENSIONS


def textual_form(rel_path: str, raw: bytes) -> tuple[str | None, str]:
    """Return the diffable text for one file's bytes, and which form it is.

    A serialized payload has no readable text of its own. Rendering it with
    replacement characters and diffing that produces mojibake, so a payload a
    maintained reader owns is rendered through that reader instead, and one no
    reader owns gets no text at all.
    """

    try:
        return raw.decode("utf-8-sig"), TEXT_KIND_PLAIN
    except UnicodeDecodeError:
        pass
    decoded = render_decoded_payload(rel_path, raw)
    if decoded is None:
        return None, TEXT_KIND_BINARY
    kind = (
        TEXT_KIND_DECODED_WHOLE
        if decoded.coverage == "whole_file"
        else TEXT_KIND_DECODED_PARTIAL
    )
    return decoded.text, kind


def modified_diff_note(scanned: "ScannedFile", text_diff: list[str] | None) -> str | None:
    """Say why a changed file shows no diff, when the reason is not obvious.

    A serialized payload can change in bytes a reader does not cover, or in
    bytes no reader reads at all. Either way the file did change, so the page
    must say what it is not showing instead of leaving an empty panel.
    """

    if text_diff:
        return None
    if scanned.text_kind == TEXT_KIND_BINARY:
        return "binary_no_reader"
    if scanned.text_kind == TEXT_KIND_TOO_LARGE:
        return "binary_too_large"
    if scanned.text_kind in (TEXT_KIND_DECODED_WHOLE, TEXT_KIND_DECODED_PARTIAL):
        return "decoded_identical"
    return None


def build_text_diff(
    old_text: str | None,
    new_text: str | None,
    *,
    fromfile: str = "previous",
    tofile: str = "current",
) -> tuple[list[str] | None, bool]:
    if old_text is None or new_text is None:
        return None, False
    diff = list(
        difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile=fromfile,
            tofile=tofile,
            lineterm="",
            n=3,
        )
    )
    if len(diff) > TEXT_DIFF_MAX_LINES:
        return diff[:TEXT_DIFF_MAX_LINES], True
    return diff or None, False


def scan_file(
    path: str, count_lines: bool, capture_text: bool, rel_path: str
) -> tuple[str, int | None, str | None, str | None]:
    digest = hashlib.blake2b(digest_size=16)
    line_count = 0
    last_byte: bytes | None = None
    has_nul = False
    text_chunks: list[bytes] | None = [] if capture_text else None
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(READ_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
            if text_chunks is not None:
                text_chunks.append(chunk)
            if count_lines:
                line_count += chunk.count(b"\n")
                last_byte = chunk[-1:]
                has_nul = has_nul or b"\x00" in chunk
    return finish_text_scan(
        digest.hexdigest(),
        rel_path,
        count_lines=count_lines,
        line_count=line_count,
        last_byte=last_byte,
        has_nul=has_nul,
        captured=None if text_chunks is None else b"".join(text_chunks),
    )


def finish_text_scan(
    digest: str,
    rel_path: str,
    *,
    count_lines: bool,
    line_count: int,
    last_byte: bytes | None,
    has_nul: bool,
    captured: bytes | None,
) -> tuple[str, int | None, str | None, str | None]:
    """The line count, diffable text and text kind of one scanned file's bytes."""

    if count_lines and last_byte is not None and last_byte != b"\n":
        line_count += 1
    if not count_lines:
        return digest, None, None, None
    if captured is None:
        # Over the diff size limit, so the bytes were never held. A NUL still
        # proves the file is not text, so its stray line feeds are not reported
        # as lines and the page can say why there is no diff -- the size, not a
        # missing reader.
        if has_nul:
            return digest, None, None, TEXT_KIND_TOO_LARGE
        return digest, line_count, None, None
    text_content, kind = textual_form(rel_path, captured)
    if text_content is None:
        return digest, None, None, kind
    if kind != TEXT_KIND_PLAIN:
        # "Lines" must describe the text actually diffed, not the payload's
        # stray line-feed bytes, or a decoded diff and its line delta disagree.
        line_count = len(text_content.splitlines())
    return digest, line_count, text_content, kind


@dataclasses.dataclass
class ExportStores:
    """The stores of one export root that the scanner expands (either may be absent)."""

    unity: UnityObjectStore | None = None
    game_files: GameFileStore | None = None

    @classmethod
    def open(cls, root: Path) -> "ExportStores":
        """Open whichever stores the root has, each on its own read-only handle."""

        unity_path = root / UNITY_STORE_RELATIVE_PATH
        game_files_path = root / GAME_FILE_STORE_RELATIVE_PATH
        stores = cls()
        try:
            stores.unity = UnityObjectStore(unity_path) if unity_path.is_file() else None
            stores.game_files = GameFileStore(game_files_path) if game_files_path.is_file() else None
        except BaseException:
            stores.close()
            raise
        return stores

    def read_row(self, row: StoreRowRef) -> bytes:
        if row.store == STORE_GAME_FILES:
            if self.game_files is None:
                raise RuntimeError(f"game-file row {row.type_name}/{row.name} was queued without its store")
            return self.game_files.read_bytes(f"{row.type_name}/{row.name}")
        if self.unity is None:
            raise RuntimeError(f"Unity row {row.type_name}/{row.name} was queued without its store")
        return self.unity.read_bytes(row.type_name, row.name)

    def close(self) -> None:
        for store in (self.unity, self.game_files):
            if store is not None:
                store.close()


def scan_store_row(
    stores: ExportStores,
    row: StoreRowRef,
    digest: str,
    count_lines: bool,
    capture_text: bool,
    rel_path: str,
) -> tuple[str, int | None, str | None, str | None]:
    """:func:`scan_file` for one store row, whose SHA256 is already known.

    The row's bytes are read only when a loose file would have been read past
    its digest: for a text extension, to count lines and capture diff text.
    """

    if not count_lines:
        return digest, None, None, None
    data = stores.read_row(row)
    return finish_text_scan(
        digest,
        rel_path,
        count_lines=True,
        line_count=data.count(b"\n"),
        last_byte=data[-1:] or None,
        has_nul=b"\x00" in data,
        captured=data if capture_text else None,
    )


def should_ignore_path(rel_path: str, ignored_exact_paths: set[str], ignored_dir_prefixes: tuple[str, ...]) -> bool:
    if rel_path in ignored_exact_paths:
        return True
    return any(rel_path.startswith(prefix) for prefix in ignored_dir_prefixes)


def build_include_roots(root: Path, include_relative_paths: Iterable[str]) -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()
    root_resolved = root.resolve()
    for raw_path in include_relative_paths:
        rel_path = normalize_cli_relative_path(str(raw_path or ""))
        candidate = root if not rel_path or rel_path == "." else root / rel_path
        try:
            resolved = candidate.resolve()
            resolved.relative_to(root_resolved)
        except ValueError:
            print(
                f"[updates_scanner] Ignoring include path outside root: {raw_path}",
                file=sys.stderr,
            )
            continue
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        roots.append(resolved)
    return roots or [root]


def file_scan_entry(root: Path, path: Path) -> ExportFileEntry | None:
    try:
        stat_result = path.stat()
    except FileNotFoundError:
        return None
    if not path.is_file():
        return None
    rel_path = normalize_relative_path(str(path.relative_to(root)))
    extension = path.suffix.lower()
    return ExportFileEntry(rel_path, str(path), stat_result.st_size, stat_result.st_mtime_ns, extension)


def unity_store_scope(rel_path: str) -> tuple[bool, str | None] | None:
    """Which store rows an include root covers, as ``(all_types, type_name)``.

    ``None`` means the include root reaches no store row. The export root,
    ``game``, ``game/Unity`` and the store file cover every row;
    ``game/Unity/<Type>`` covers one type. A deeper include path names no
    row, because the store keys rows by type folder and file name only.
    """

    lower = rel_path.lower()
    if rel_path in ("", ".") or lower in ("game", UNITY_STORE_UNITY_PREFIX.lower(), UNITY_STORE_RELATIVE_PATH.lower()):
        return True, None
    prefix = UNITY_STORE_UNITY_PREFIX.lower() + "/"
    if lower.startswith(prefix):
        rest = rel_path[len(prefix):]
        if rest and "/" not in rest:
            return False, rest
    return None


def iter_unity_store_entries(
    store: UnityObjectStore,
    type_name: str | None,
    ignored_exact_paths: set[str],
    ignored_dir_prefixes: tuple[str, ...],
) -> Iterable[ExportFileEntry]:
    """One virtual entry per store row, at its ``game/Unity/<Type>/<name>`` path."""

    for row in store.iter_rows(type_name):
        row_type, name = row.type, row.name
        rel_path = logical_ref(row_type, name)
        if should_ignore_path(rel_path, ignored_exact_paths, ignored_dir_prefixes):
            continue
        yield ExportFileEntry(
            rel_path=rel_path,
            full_path=str(store.path),
            size=int(row.size),
            mtime_ns=int(row.mtime_ns),
            extension=Path(name).suffix.lower(),
            store_row=StoreRowRef(row_type, name, STORE_UNITY),
            store_digest=str(row.sha256),
        )


def game_file_store_scope(rel_path: str) -> list[tuple[str, str | None]] | None:
    """Which game-file store rows an include root covers.

    Returns ``[(packed folder, path prefix inside it or None), ...]``, or
    ``None`` when the include root reaches no row. The export root, ``game``
    and the store file cover every packed folder; an ancestor of a packed
    folder (``game/Json``) or the folder itself covers that whole folder; a
    path inside a packed folder (``game/Json/LipSync/Chinese``, or one file)
    covers the rows at or under it. Matching is case-insensitive, as the
    include root would be on disk.
    """

    lower = rel_path.lower()
    if rel_path in ("", ".") or lower in ("game", GAME_FILE_STORE_RELATIVE_PATH.lower()):
        return [(folder, None) for folder in PACKED_GAME_DIRS]
    if not lower.startswith("game/"):
        return None
    inside_game = rel_path[len("game/"):].strip("/")
    key = inside_game.casefold()
    scopes: list[tuple[str, str | None]] = []
    for folder in PACKED_GAME_DIRS:
        folder_key = folder.casefold()
        if key == folder_key or folder_key.startswith(key + "/"):
            scopes.append((folder, None))
        elif key.startswith(folder_key + "/"):
            scopes.append((folder, inside_game[len(folder) + 1:]))
    return scopes or None


def iter_game_file_store_entries(
    store: GameFileStore,
    folder: str,
    prefix: str | None,
    ignored_exact_paths: set[str],
    ignored_dir_prefixes: tuple[str, ...],
) -> Iterable[ExportFileEntry]:
    """One virtual entry per row of one packed folder, at its ``game/<path>``."""

    prefix_key = None if prefix is None else prefix.casefold()
    for row in store.iter_rows(folder):
        inside = row.path[len(folder) + 1:]
        if prefix_key is not None:
            inside_key = inside.casefold()
            if not (inside_key == prefix_key or inside_key.startswith(prefix_key + "/")):
                continue
        rel_path = row.ref
        if should_ignore_path(rel_path, ignored_exact_paths, ignored_dir_prefixes):
            continue
        yield ExportFileEntry(
            rel_path=rel_path,
            full_path=str(store.path),
            size=int(row.size),
            mtime_ns=int(row.mtime_ns),
            extension=Path(inside).suffix.lower(),
            store_row=StoreRowRef(folder, inside, STORE_GAME_FILES),
            store_digest=str(row.sha256),
        )


def iter_export_files(
    root: Path,
    ignored_exact_paths: set[str],
    ignored_dir_prefixes: tuple[str, ...],
    include_relative_paths: Iterable[str] = (),
    unity_store: UnityObjectStore | None = None,
    game_file_store: GameFileStore | None = None,
) -> Iterable[ExportFileEntry]:
    """Every file under the include roots, with the export stores expanded.

    ``game/Unity.sqlite``, ``game/GameFiles.sqlite`` and their SQLite
    sidecars are never yielded as files, and nothing on disk under a packed
    game folder is walked. When a store is given, its rows are yielded at
    their logical paths for every include root that covers them; without it
    that store is simply skipped.
    """

    yielded_paths: set[str] = set()
    include_roots = build_include_roots(root, include_relative_paths)
    stack = list(reversed(include_roots))
    while stack:
        current = stack.pop()
        if current.is_file():
            scan_entry = file_scan_entry(root, current)
            if scan_entry is None:
                continue
            rel_path = scan_entry.rel_path
            if is_export_store_relative_path(rel_path) or is_packed_game_relative_path(rel_path):
                continue
            if should_ignore_path(rel_path, ignored_exact_paths, ignored_dir_prefixes):
                continue
            if rel_path in yielded_paths:
                continue
            yielded_paths.add(rel_path)
            yield scan_entry
            continue
        try:
            with os.scandir(current) as entries:
                ordered_entries = sorted(entries, key=lambda entry: entry.name)
        except FileNotFoundError:
            continue
        for entry in reversed(ordered_entries):
            full_path = Path(entry.path)
            rel_path = normalize_relative_path(str(full_path.relative_to(root)))
            if entry.is_dir(follow_symlinks=False):
                if should_ignore_path(rel_path, ignored_exact_paths, ignored_dir_prefixes):
                    continue
                if is_packed_game_relative_path(rel_path):
                    continue
                stack.append(full_path)
                continue
            if not entry.is_file(follow_symlinks=False):
                continue
            if is_export_store_relative_path(rel_path) or is_packed_game_relative_path(rel_path):
                continue
            if should_ignore_path(rel_path, ignored_exact_paths, ignored_dir_prefixes):
                continue
            if rel_path in yielded_paths:
                continue
            yielded_paths.add(rel_path)
            stat_result = entry.stat(follow_symlinks=False)
            extension = full_path.suffix.lower()
            yield ExportFileEntry(rel_path, str(full_path), stat_result.st_size, stat_result.st_mtime_ns, extension)

    include_rels = [try_relative_to(include_root, root) for include_root in include_roots]
    if unity_store is not None and not should_ignore_path(
        UNITY_STORE_RELATIVE_PATH, ignored_exact_paths, ignored_dir_prefixes
    ):
        yield from _iter_unity_scope_entries(
            unity_store, include_rels, ignored_exact_paths, ignored_dir_prefixes, yielded_paths
        )
    if game_file_store is not None and not should_ignore_path(
        GAME_FILE_STORE_RELATIVE_PATH, ignored_exact_paths, ignored_dir_prefixes
    ):
        yield from _iter_game_file_scope_entries(
            game_file_store, include_rels, ignored_exact_paths, ignored_dir_prefixes, yielded_paths
        )


def _iter_game_file_scope_entries(
    store: GameFileStore,
    include_rels: list[str | None],
    ignored_exact_paths: set[str],
    ignored_dir_prefixes: tuple[str, ...],
    yielded_paths: set[str],
) -> Iterable[ExportFileEntry]:
    scopes: list[tuple[str, str | None]] = []
    for rel in include_rels:
        for scope in (None if rel is None else game_file_store_scope(rel)) or ():
            if scope not in scopes:
                scopes.append(scope)
    # A folder-wide scope covers every narrower scope of the same folder.
    whole = {folder for folder, prefix in scopes if prefix is None}
    scopes = [scope for scope in scopes if scope[1] is None or scope[0] not in whole]
    for folder, prefix in sorted(scopes, key=lambda item: (item[0], item[1] or "")):
        for store_entry in iter_game_file_store_entries(
            store, folder, prefix, ignored_exact_paths, ignored_dir_prefixes
        ):
            # Overlapping include prefixes may reach the same row twice.
            if store_entry.rel_path in yielded_paths:
                continue
            yielded_paths.add(store_entry.rel_path)
            yield store_entry


def _iter_unity_scope_entries(
    unity_store: UnityObjectStore,
    include_rels: list[str | None],
    ignored_exact_paths: set[str],
    ignored_dir_prefixes: tuple[str, ...],
    yielded_paths: set[str],
) -> Iterable[ExportFileEntry]:
    all_types = False
    type_names: list[str] = []
    for rel in include_rels:
        scope = None if rel is None else unity_store_scope(rel)
        if scope is None:
            continue
        if scope[0]:
            all_types = True
            break
        if scope[1] not in type_names:
            type_names.append(scope[1])
    for type_name in [None] if all_types else sorted(type_names):
        for store_entry in iter_unity_store_entries(
            unity_store, type_name, ignored_exact_paths, ignored_dir_prefixes
        ):
            # A loose document at the same logical path does not belong in a
            # v3 root; if one exists it was yielded above and keeps its entry.
            if store_entry.rel_path in yielded_paths:
                continue
            yielded_paths.add(store_entry.rel_path)
            yield store_entry


def ensure_database_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            size INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            digest TEXT NOT NULL,
            line_count INTEGER,
            extension TEXT NOT NULL,
            text_content TEXT,
            text_kind TEXT
        )
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(files)")}
    if "text_content" not in columns:
        conn.execute("ALTER TABLE files ADD COLUMN text_content TEXT")
    if "text_kind" not in columns:
        conn.execute("ALTER TABLE files ADD COLUMN text_kind TEXT")
    conn.commit()


def prepare_scan_table(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS files_scan")
    conn.execute(
        """
        CREATE TABLE files_scan (
            path TEXT PRIMARY KEY,
            size INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            digest TEXT NOT NULL,
            line_count INTEGER,
            extension TEXT NOT NULL,
            text_content TEXT,
            text_kind TEXT
        )
        """
    )


def batch_insert_rows(conn: sqlite3.Connection, rows: list[SnapshotRow]) -> None:
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO files_scan (path, size, mtime_ns, digest, line_count, extension, text_content, text_kind)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row.path,
                row.size,
                row.mtime_ns,
                row.digest,
                row.line_count,
                row.extension,
                row.text_content,
                row.text_kind,
            )
            for row in rows
        ],
    )
    rows.clear()


def submit_pending_scan(
    executor: concurrent.futures.Executor,
    item: PendingFile,
    stores: ExportStores | None,
) -> concurrent.futures.Future:
    if item.store_row is None:
        return executor.submit(scan_file, item.full_path, item.count_lines, item.capture_text, item.rel_path)
    if stores is None or item.store_digest is None:
        raise RuntimeError(f"store row {item.rel_path} was queued without its store")
    return executor.submit(
        scan_store_row,
        stores,
        item.store_row,
        item.store_digest,
        item.count_lines,
        item.capture_text,
        item.rel_path,
    )


def process_pending_batch(
    pending_batch: list[PendingFile],
    conn: sqlite3.Connection,
    accumulator: ChangeAccumulator,
    executor: concurrent.futures.Executor,
    stores: ExportStores | None = None,
) -> None:
    if not pending_batch:
        return

    insert_rows: list[SnapshotRow] = []
    future_map = {submit_pending_scan(executor, item, stores): item for item in pending_batch}
    for future in concurrent.futures.as_completed(future_map):
        item = future_map[future]
        digest, line_count, text_content, text_kind = future.result()
        scanned = ScannedFile(
            rel_path=item.rel_path,
            size=item.size,
            mtime_ns=item.mtime_ns,
            extension=item.extension,
            digest=digest,
            line_count=line_count,
            text_content=text_content,
            old_size=item.old_size,
            old_digest=item.old_digest,
            old_line_count=item.old_line_count,
            old_text_content=item.old_text_content,
            text_kind=text_kind,
            old_text_kind=item.old_text_kind,
        )
        insert_rows.append(
            SnapshotRow(
                path=item.rel_path,
                size=item.size,
                mtime_ns=item.mtime_ns,
                digest=digest,
                line_count=line_count,
                extension=item.extension,
                text_content=text_content,
                text_kind=text_kind,
            )
        )
        if item.old_digest is None:
            accumulator.record_added(scanned)
        elif item.old_digest != digest:
            accumulator.record_modified(scanned)
        else:
            accumulator.note_metadata_only_update()

    batch_insert_rows(conn, insert_rows)
    pending_batch.clear()


def read_old_row(
    select_cursor: sqlite3.Cursor, rel_path: str
) -> tuple[int, int, str, int | None, str, str | None, str | None] | None:
    row = select_cursor.execute(
        "SELECT size, mtime_ns, digest, line_count, extension, text_content, text_kind "
        "FROM files WHERE path = ?",
        (rel_path,),
    ).fetchone()
    if row is None:
        return None
    return (
        int(row[0]),
        int(row[1]),
        str(row[2]),
        (None if row[3] is None else int(row[3])),
        str(row[4]),
        None if row[5] is None else str(row[5]),
        None if row[6] is None else str(row[6]),
    )


def find_deleted_rows(
    conn: sqlite3.Connection,
) -> Iterable[tuple[str, int, str, int | None, str, str | None, str | None]]:
    return conn.execute(
        """
        SELECT files.path, files.size, files.digest, files.line_count, files.extension,
               files.text_content, files.text_kind
        FROM files
        LEFT JOIN files_scan ON files.path = files_scan.path
        WHERE files_scan.path IS NULL
        ORDER BY files.path
        """
    )


def format_counter(counter: Counter[str], limit: int = 15) -> list[str]:
    lines = []
    for extension, count in counter.most_common(limit):
        lines.append(f"- `{extension}`: {count}")
    return lines


def format_change_entry(entry: ChangeEntry) -> str:
    bits = [f"`{entry.path}`"]
    if entry.old_size is not None and entry.new_size is not None:
        bits.append(f"size {entry.old_size} -> {entry.new_size}")
    elif entry.new_size is not None:
        bits.append(f"size {entry.new_size}")
    elif entry.old_size is not None:
        bits.append(f"size {entry.old_size}")
    if entry.old_line_count is not None and entry.new_line_count is not None:
        delta = entry.new_line_count - entry.old_line_count
        bits.append(f"lines {entry.old_line_count} -> {entry.new_line_count} ({delta:+d})")
    elif entry.new_line_count is not None:
        bits.append(f"lines {entry.new_line_count}")
    elif entry.old_line_count is not None:
        bits.append(f"lines {entry.old_line_count}")
    return ", ".join(bits)


def change_entry_from_dict(payload: dict[str, object]) -> ChangeEntry:
    return ChangeEntry(
        path=str(payload["path"]),
        extension=str(payload["extension"]),
        old_size=None if payload.get("old_size") is None else int(payload["old_size"]),
        new_size=None if payload.get("new_size") is None else int(payload["new_size"]),
        old_line_count=None
        if payload.get("old_line_count") is None
        else int(payload["old_line_count"]),
        new_line_count=None
        if payload.get("new_line_count") is None
        else int(payload["new_line_count"]),
        text_diff=list(payload.get("text_diff") or []) or None,
        text_diff_truncated=bool(payload.get("text_diff_truncated")),
        text_kind=None if payload.get("text_kind") is None else str(payload["text_kind"]),
        text_diff_note=(
            None if payload.get("text_diff_note") is None else str(payload["text_diff_note"])
        ),
    )


def write_reports(
    payload: dict[str, object],
    summary_md_path: Path,
    summary_json_path: Path,
    history_dir: Path | None,
    write_history: bool,
) -> None:
    started_at = dt.datetime.fromisoformat(str(payload["started_at"]))
    finished_at = dt.datetime.fromisoformat(str(payload["finished_at"]))
    changes = payload["changes"]
    breakdown = payload["breakdown"]
    samples = payload["samples"]

    markdown_lines = [
        "# Export change summary",
        "",
        f"- Scan started: `{started_at.isoformat()}`",
        f"- Scan finished: `{finished_at.isoformat()}`",
        f"- Duration: `{payload['duration_seconds']}` seconds",
        f"- Files scanned: `{payload['scanned_files']}`",
        "",
        "## Totals",
        "",
        f"- Added: `{changes['added']}`",
        f"- Modified: `{changes['modified']}`",
        f"- Deleted: `{changes['deleted']}`",
        f"- Metadata-only updates: `{changes['metadata_only_updates']}`",
        f"- Exact metadata matches reused from cache: `{changes['reused_metadata_matches']}`",
        "",
        "## Added by extension",
        "",
    ]
    markdown_lines.extend(format_counter(Counter(breakdown["added_by_extension"])))
    markdown_lines.extend(
        [
            "",
            "## Modified by extension",
            "",
        ]
    )
    markdown_lines.extend(format_counter(Counter(breakdown["modified_by_extension"])))
    markdown_lines.extend(
        [
            "",
            "## Deleted by extension",
            "",
        ]
    )
    markdown_lines.extend(format_counter(Counter(breakdown["deleted_by_extension"])))

    if samples["largest_line_changes"]:
        markdown_lines.extend(
            [
                "",
                "## Biggest text line deltas",
                "",
            ]
        )
        markdown_lines.extend(
            f"- {format_change_entry(change_entry_from_dict(entry))}"
            for entry in samples["largest_line_changes"]
        )

    for title, key in (
        ("Added samples", "added"),
        ("Modified samples", "modified"),
        ("Deleted samples", "deleted"),
    ):
        entries = samples[key]
        if not entries:
            continue
        markdown_lines.extend(["", f"## {title}", ""])
        markdown_lines.extend(
            f"- {format_change_entry(change_entry_from_dict(entry))}" for entry in entries[:25]
        )
        if len(entries) > 25:
            markdown_lines.append(f"- ... {len(entries) - 25} more captured in the JSON summary")

    markdown = "\n".join(markdown_lines) + "\n"

    summary_md_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_md_path.write_text(markdown, encoding="utf-8")
    summary_json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if not write_history or history_dir is None:
        return

    history_dir.mkdir(parents=True, exist_ok=True)
    stamp = finished_at.strftime("%Y%m%d-%H%M%S")
    history_md = history_dir / f"export-change-summary-{stamp}.md"
    history_json = history_dir / f"export-change-summary-{stamp}.json"
    history_md.write_text(markdown, encoding="utf-8")
    history_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def print_progress(prefix: str, processed: int, started_at: float) -> None:
    elapsed = max(time.monotonic() - started_at, 0.001)
    rate = processed / elapsed
    print(f"[updates_scanner] {prefix}: {processed} files ({rate:.1f}/s)")


def build_ignore_rules(config: ScanConfig, root: Path) -> tuple[set[str], tuple[str, ...]]:
    ignored_exact_paths: set[str] = set()
    ignored_dir_prefixes: set[str] = set()

    paths_to_check = [config.state_dir, config.summary_md, config.summary_json]
    if config.history_dir is not None:
        paths_to_check.append(config.history_dir)

    for path in paths_to_check:
        rel_path = try_relative_to(Path(path), root)
        if rel_path is None or rel_path == ".":
            continue
        ignored_exact_paths.add(rel_path)
        ignored_dir_prefixes.add(f"{rel_path}/")

    for raw_path in config.ignore_relative_paths:
        rel_path = normalize_cli_relative_path(raw_path)
        if not rel_path:
            continue
        ignored_exact_paths.add(rel_path)
        ignored_dir_prefixes.add(f"{rel_path}/")

    return ignored_exact_paths, tuple(sorted(ignored_dir_prefixes))


def scan_export_changes(config: ScanConfig) -> ScanResult:
    """Compare ``config.root`` with its cached snapshot and write reports."""

    if config.workers < 1:
        raise ValueError("workers must be at least 1")
    if config.hash_batch_size < 1:
        raise ValueError("hash_batch_size must be at least 1")
    if config.sample_limit < 0 or config.top_line_limit < 0:
        raise ValueError("report limits cannot be negative")

    root = config.root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Export root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Export root is not a directory: {root}")

    ignored_exact_paths, ignored_dir_prefixes = build_ignore_rules(config, root)

    config.state_dir.mkdir(parents=True, exist_ok=True)
    db_path = config.state_dir / "state.sqlite3"

    started_at = dt.datetime.now(dt.timezone.utc).astimezone()
    monotonic_start = time.monotonic()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    ensure_database_schema(conn)
    prepare_scan_table(conn)

    accumulator = ChangeAccumulator(
        sample_limit=config.sample_limit,
        top_line_limit=config.top_line_limit,
    )

    select_cursor = conn.cursor()
    unchanged_rows: list[SnapshotRow] = []
    pending_batch: list[PendingFile] = []
    stores: ExportStores | None = None

    try:
        stores = ExportStores.open(root)
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.workers) as executor:
            with conn:
                for scan_entry in iter_export_files(
                    root,
                    ignored_exact_paths,
                    ignored_dir_prefixes,
                    config.include_relative_paths,
                    stores.unity,
                    stores.game_files,
                ):
                    rel_path, full_path, size, mtime_ns, extension = scan_entry[:5]
                    accumulator.note_scan()
                    old_row = read_old_row(select_cursor, rel_path)
                    if old_row is not None:
                        (
                            old_size,
                            old_mtime_ns,
                            old_digest,
                            old_line_count,
                            old_extension,
                            old_text_content,
                            old_text_kind,
                        ) = old_row
                        should_capture_text = is_text_extension(extension) and size <= TEXT_DIFF_MAX_BYTES
                        # A payload with no diffable text is still fully
                        # scanned: the recorded kind, not the text, says so.
                        has_cached_text = (
                            not should_capture_text
                            or old_text_content is not None
                            or old_text_kind is not None
                        )
                        # A store row carries its content hash, so it is
                        # unchanged exactly when the hash is; a file falls
                        # back to its size and modification time.
                        if scan_entry.store_digest is not None:
                            metadata_match = scan_entry.store_digest == old_digest and size == old_size
                        else:
                            metadata_match = size == old_size and mtime_ns == old_mtime_ns
                        if metadata_match and has_cached_text:
                            accumulator.note_reused_metadata_match()
                            unchanged_rows.append(
                                SnapshotRow(
                                    path=rel_path,
                                    size=size,
                                    mtime_ns=mtime_ns,
                                    digest=old_digest,
                                    line_count=old_line_count,
                                    extension=old_extension,
                                    text_content=old_text_content,
                                    text_kind=old_text_kind,
                                )
                            )
                            if len(unchanged_rows) >= config.hash_batch_size:
                                batch_insert_rows(conn, unchanged_rows)
                            if accumulator.scanned_files % PROGRESS_EVERY_FILES == 0:
                                print_progress("scanned", accumulator.scanned_files, monotonic_start)
                            continue
                    else:
                        old_size = None
                        old_digest = None
                        old_line_count = None
                        old_text_content = None
                        old_text_kind = None

                    is_text = is_text_extension(extension)
                    pending_batch.append(
                        PendingFile(
                            rel_path=rel_path,
                            full_path=full_path,
                            size=size,
                            mtime_ns=mtime_ns,
                            extension=extension,
                            count_lines=is_text,
                            capture_text=is_text and size <= TEXT_DIFF_MAX_BYTES,
                            old_size=old_size,
                            old_digest=old_digest,
                            old_line_count=old_line_count,
                            old_text_content=old_text_content,
                            old_text_kind=old_text_kind,
                            store_row=scan_entry.store_row,
                            store_digest=scan_entry.store_digest,
                        )
                    )
                    if len(pending_batch) >= config.hash_batch_size:
                        process_pending_batch(pending_batch, conn, accumulator, executor, stores)
                    if accumulator.scanned_files % PROGRESS_EVERY_FILES == 0:
                        print_progress("scanned", accumulator.scanned_files, monotonic_start)

                batch_insert_rows(conn, unchanged_rows)
                process_pending_batch(pending_batch, conn, accumulator, executor, stores)

                for (
                    rel_path,
                    old_size,
                    old_digest,
                    old_line_count,
                    extension,
                    old_text_content,
                    old_text_kind,
                ) in find_deleted_rows(conn):
                    accumulator.record_deleted(
                        rel_path,
                        extension,
                        int(old_size),
                        None if old_line_count is None else int(old_line_count),
                        old_text_content,
                        old_text_kind,
                    )

                conn.execute("DROP TABLE files")
                conn.execute("ALTER TABLE files_scan RENAME TO files")
    finally:
        conn.close()
        if stores is not None:
            stores.close()

    finished_at = dt.datetime.now(dt.timezone.utc).astimezone()
    payload = accumulator.to_dict(started_at, finished_at)
    include_paths = [
        normalize_cli_relative_path(path)
        for path in config.include_relative_paths
        if normalize_cli_relative_path(path)
    ]
    if include_paths:
        payload["scan_scope"] = {
            "mode": "include_relative_paths",
            "include_relative_paths": include_paths,
        }
    summary_md_path = config.summary_md.resolve()
    summary_json_path = config.summary_json.resolve()
    write_reports(
        payload=payload,
        summary_md_path=summary_md_path,
        summary_json_path=summary_json_path,
        history_dir=config.history_dir,
        write_history=config.history_dir is not None,
    )

    print(
        "[updates_scanner] Done:"
        f" added={accumulator.added_count},"
        f" modified={accumulator.modified_count},"
        f" deleted={accumulator.deleted_count},"
        f" metadata_only={accumulator.metadata_only_updates},"
        f" scanned={accumulator.scanned_files}"
    )
    print(f"[updates_scanner] Summary: {summary_md_path}")
    print(f"[updates_scanner] JSON: {summary_json_path}")
    if config.history_dir is not None:
        print(f"[updates_scanner] History directory: {config.history_dir}")
    return ScanResult(
        payload=payload,
        summary_json=summary_json_path,
        summary_md=summary_md_path,
    )
