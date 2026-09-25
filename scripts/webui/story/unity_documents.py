"""Path-shaped access to exported Unity object documents for Story and Mission Pipeline readers.

Layout v3 keeps every exported Unity object document (``.json``, ``.anim``) in
the export's object store (``game/Unity.sqlite``, see
``scripts/game_data/unity_store.py``) instead of loose files under
``game/Unity/<Type>/``. Story and Mission Pipeline readers identify a document
by the path it used to have, ``<export root>/game/Unity/<Type>/<name>``, and
publish that path as provenance. These helpers keep that identity:

- a *store type directory* is ``<export root>/game/Unity/<Type>``; globbing it
  lists the store's rows of that type as those logical paths, and reading such
  a path reads the stored bytes. A document missing from the store is missing:
  there is no fallback to a loose file at that path;
- any other directory (a focused AnimeStudio CLI extraction under the work or
  tmp tree) is read from disk as before, because those are separate tool
  outputs, not the published export.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Iterator

from scripts.common import fast_glob_files, sha256_file
from scripts.game_data.unity_store import (
    UnityObjectRow,
    UnityObjectStore,
    is_store_file,
    open_store,
    open_store_if_present,
)

_MASK64 = (1 << 64) - 1


def _signed64(value: int) -> int:
    value &= _MASK64
    return value - (1 << 64) if value >= (1 << 63) else value


def store_type_dir_parts(directory: Path | str) -> tuple[Path, str] | None:
    """``(export root, Unity type)`` for a ``<root>/game/Unity/<Type>`` directory, else None."""
    directory = Path(directory)
    parent = directory.parent
    if parent.name == "Unity" and parent.parent.name == "game" and directory.name:
        return parent.parent.parent, directory.name
    return None


def is_store_type_dir(directory: Path | str) -> bool:
    return store_type_dir_parts(directory) is not None


def document_parts(path: Path | str) -> tuple[Path, str, str] | None:
    """``(export root, type, name)`` for a stored document's logical path, else None."""
    path = Path(path)
    parts = store_type_dir_parts(path.parent)
    if parts is None or not is_store_file(path.name):
        return None
    return parts[0], parts[1], path.name


def type_dir_store(directory: Path | str, *, required: bool = False) -> UnityObjectStore | None:
    """The object store behind a store type directory (None when the export has none)."""
    parts = store_type_dir_parts(directory)
    if parts is None:
        return None
    return open_store(parts[0]) if required else open_store_if_present(parts[0])


def document_dir_present(directory: Path | str) -> bool:
    """True when a document directory has anything to read.

    A store type directory is present when the export's store holds at least
    one document of that type; any other directory when it exists on disk.
    """
    parts = store_type_dir_parts(directory)
    if parts is None:
        return Path(directory).is_dir()
    store = open_store_if_present(parts[0])
    return store is not None and store.count(parts[1]) > 0


def document_count(directory: Path | str, pattern: str = "*.json") -> int:
    parts = store_type_dir_parts(directory)
    if parts is None:
        return len(fast_glob_files(Path(directory), pattern))
    store = open_store_if_present(parts[0])
    return len(store.names(parts[1], pattern)) if store is not None else 0


def document_path(directory: Path | str, row: UnityObjectRow) -> Path:
    return Path(directory) / row.name


def glob_documents(directory: Path | str, pattern: str) -> list[Path]:
    """Documents in one directory matching a case-insensitive file-name glob, sorted by name.

    Store type directories list the store (flat, so a recursive walk is the
    same query); other directories use the Win32-accelerated file glob.
    """
    directory = Path(directory)
    parts = store_type_dir_parts(directory)
    if parts is None or not is_store_file(pattern):
        return fast_glob_files(directory, pattern)
    store = open_store_if_present(parts[0])
    if store is None:
        return []
    return [directory / name for name in store.names(parts[1], pattern)]


def documents_by_path_id(directory: Path | str, path_id: int) -> list[Path]:
    """Documents of one directory whose exported ``_p<PathID>`` names ``path_id``.

    The store answers from its PathID index; a loose directory by file name.
    """
    directory = Path(directory)
    parts = store_type_dir_parts(directory)
    suffix = f"{int(path_id) & _MASK64:016X}"
    if parts is None:
        paths = set(fast_glob_files(directory, f"*_p{suffix}.json"))
        if sys.platform != "win32":
            paths.update(fast_glob_files(directory, f"*_p{suffix.lower()}.json"))
        return sorted(paths)
    store = open_store_if_present(parts[0])
    if store is None:
        return []
    return [
        directory / row.name
        for row in store.rows_by_path_id(_signed64(int(path_id)))
        if row.type == parts[1] and row.name.lower().endswith(".json")
    ]


def iter_document_bytes(directory: Path | str, pattern: str) -> Iterator[tuple[Path, bytes]]:
    """Every matching document with its bytes, in name order, in one pass."""
    directory = Path(directory)
    parts = store_type_dir_parts(directory)
    if parts is None or not is_store_file(pattern):
        for path in fast_glob_files(directory, pattern):
            yield path, path.read_bytes()
        return
    store = open_store_if_present(parts[0])
    if store is None:
        return
    for row, data in store.iter_documents(parts[1], pattern):
        yield directory / row.name, data


def document_row(path: Path | str) -> UnityObjectRow | None:
    parts = document_parts(path)
    if parts is None:
        return None
    store = open_store_if_present(parts[0])
    return store.row(parts[1], parts[2]) if store is not None else None


def document_exists(path: Path | str) -> bool:
    parts = document_parts(path)
    if parts is None:
        return Path(path).is_file()
    store = open_store_if_present(parts[0])
    return store is not None and store.exists(parts[1], parts[2])


def read_document_bytes(path: Path | str) -> bytes:
    """The bytes of a document; a stored document missing from the store raises FileNotFoundError."""
    parts = document_parts(path)
    if parts is None:
        return Path(path).read_bytes()
    store = open_store_if_present(parts[0])
    if store is None:
        raise FileNotFoundError(f"no Unity object store for {path}")
    try:
        return store.read_bytes(parts[1], parts[2])
    except KeyError:
        raise FileNotFoundError(f"Unity object store has no {parts[1]}/{parts[2]}") from None


def read_document_text(path: Path | str, *, errors: str = "strict") -> str:
    return read_document_bytes(path).decode("utf-8-sig", errors=errors)


def read_document_json(path: Path | str) -> Any:
    return json.loads(read_document_text(path))


def document_sha256(path: Path | str) -> str:
    """Lowercase SHA-256 of a document's exact bytes (the store records it per row)."""
    parts = document_parts(path)
    if parts is None:
        return sha256_file(Path(path))
    row = document_row(path)
    if row is None:
        raise FileNotFoundError(f"Unity object store has no {parts[1]}/{parts[2]}")
    return row.sha256


def document_size(path: Path | str) -> int:
    parts = document_parts(path)
    if parts is None:
        return os.stat(path).st_size
    row = document_row(path)
    if row is None:
        raise FileNotFoundError(f"Unity object store has no {parts[1]}/{parts[2]}")
    return row.size


def document_digest(path: Path | str) -> tuple[int, str] | None:
    """``(size, uppercase SHA256)`` of a document or loose file, None when absent.

    The store-aware ``SourceDigest`` for ``scripts.common`` source checks.
    """
    try:
        return document_size(path), document_sha256(path).upper()
    except (FileNotFoundError, OSError):
        return None
