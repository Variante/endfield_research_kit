"""The export's Unity object store: every exported Unity object document in one SQLite file.

AnimeStudio exports one file per Unity object. Layout v3 publishes the text
documents among them -- the ``.json`` object dumps and the ``.anim`` YAML clips,
well over a million files -- into ``game/Unity.sqlite`` instead of
``game/Unity/<Type>/``. Converted media (PNG, OBJ, FBX, ...) stays loose under
``game/Unity/<Type>/`` because the browser and external viewers open it by path.

Each row is one former file, keyed by its Unity type folder and its exported
file name, so ``game/Unity/<Type>/<name>`` stays the logical reference every
report and published record already uses. The stored bytes are the exported
bytes exactly (zlib-compressed), with their SHA256; nothing is re-serialized.

Readers use :class:`UnityObjectStore`; the exporter and the v2 -> v3 packer use
:class:`UnityObjectStoreWriter`. For ad-hoc study, the CLI registers SQL
functions ``inflate(data)`` (the document text) and ``doc(data, '$.path')``
(``json_extract`` over it):

    python -m scripts.game_data.unity_store stats
    python -m scripts.game_data.unity_store ls MonoBehaviour "data_chr_*"
    python -m scripts.game_data.unity_store cat MonoBehaviour data_chr_0001_p0123456789ABCDEF.json
    python -m scripts.game_data.unity_store sql "SELECT name FROM objects WHERE type='TextAsset' LIMIT 5"
    python -m scripts.game_data.unity_store extract MonoBehaviour "DynamicScene*" --out tmp/study/dyn
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sqlite3
import sys
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Mapping

if __package__ in {None, ""}:
    raise SystemExit("Run as: python -m scripts.game_data.unity_store")

from scripts.source_paths import ExportLayout

STORE_SCHEMA = "endfield.unity-object-store.v1"
STORE_FILE_NAME = "Unity.sqlite"
#: Exported suffixes that are object documents and live in the store. Every
#: other suffix is converted media and stays a loose file.
STORE_SUFFIXES: tuple[str, ...] = (".json", ".anim")
ZLIB_LEVEL = 6
#: meta key listing source documents the v2 packer could not read and the
#: caller accepted as lost (``pack_unity_store --accept-unreadable``).
UNREADABLE_META_KEY = "unreadableAtPack"
_MISSING = object()
_PATH_ID_SUFFIX = re.compile(r"_p([0-9A-Fa-f]{16})(?=\.)")
_HEADER_KEY = '"$animestudio"'

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS objects (
    type TEXT NOT NULL,
    name TEXT NOT NULL COLLATE NOCASE,
    object_name TEXT,
    path_id INTEGER,
    source_file TEXT,
    script_path_id INTEGER,
    size INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    data BLOB NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS objects_type_name ON objects (type, name);
CREATE INDEX IF NOT EXISTS objects_type_object_name ON objects (type, object_name);
CREATE INDEX IF NOT EXISTS objects_path_id ON objects (path_id, source_file);
CREATE INDEX IF NOT EXISTS objects_script ON objects (script_path_id) WHERE script_path_id IS NOT NULL;
"""

_ROW_COLUMNS = "type, name, object_name, path_id, source_file, script_path_id, size, sha256, mtime_ns"


class UnityStoreError(RuntimeError):
    """The store is missing, unreadable, or not this schema."""


def is_store_file(name: str) -> bool:
    """True for an exported file name the store owns (an object document)."""
    return name.lower().endswith(STORE_SUFFIXES)


def store_path(export_root: Path) -> Path:
    return ExportLayout(export_root).unity_store_path


def logical_ref(type_name: str, name: str) -> str:
    """The ``game/Unity/<Type>/<name>`` reference a row stands for."""
    return f"game/Unity/{type_name}/{name}"


def split_logical_ref(value: str | os.PathLike[str]) -> tuple[str, str] | None:
    """``(type, name)`` for a ``.../game/Unity/<Type>/<name>`` path, else None."""
    parts = PurePosixPath(str(value).replace("\\", "/")).parts
    for index in range(len(parts) - 3, -1, -1):
        if parts[index] == "game" and parts[index + 1] == "Unity" and index + 3 == len(parts) - 1:
            return parts[index + 2], parts[index + 3]
    return None


@dataclass(frozen=True)
class UnityObjectRow:
    type: str
    name: str
    object_name: str | None
    path_id: int | None
    source_file: str | None
    script_path_id: int | None
    size: int
    sha256: str
    #: The mtime of the exported file the row was published from (0 if unknown).
    mtime_ns: int = 0

    @property
    def ref(self) -> str:
        return logical_ref(self.type, self.name)

    @property
    def stem(self) -> str:
        return self.name.rsplit(".", 1)[0] if "." in self.name else self.name


def _signed64(value: int) -> int:
    return value - (1 << 64) if value >= (1 << 63) else value


def path_id_from_name(name: str) -> int | None:
    match = _PATH_ID_SUFFIX.search(name)
    return _signed64(int(match.group(1), 16)) if match else None


def _glob_prefix(pattern: str) -> str:
    cut = len(pattern)
    for token in "*?[":
        position = pattern.find(token)
        if position >= 0:
            cut = min(cut, position)
    return pattern[:cut]


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def describe_document(name: str, data: bytes) -> dict[str, Any]:
    """The indexed columns for one document: from its AnimeStudio header when it has one."""
    info: dict[str, Any] = {
        "object_name": None,
        "path_id": path_id_from_name(name),
        "source_file": None,
        "script_path_id": None,
    }
    if name.lower().endswith(".json"):
        text = data[:65536].decode("utf-8-sig", errors="replace")
        key = text.find(_HEADER_KEY)
        start = text.find("{", key + len(_HEADER_KEY)) if key >= 0 else -1
        header: Any = None
        if start >= 0:
            try:
                header, _ = json.JSONDecoder().raw_decode(text, start)
            except json.JSONDecodeError:
                full = data.decode("utf-8-sig", errors="replace")
                try:
                    header, _ = json.JSONDecoder().raw_decode(full, full.find("{", full.find(_HEADER_KEY) + len(_HEADER_KEY)))
                except (json.JSONDecodeError, ValueError):
                    header = None
        if isinstance(header, dict):
            if isinstance(header.get("pathId"), int):
                info["path_id"] = header["pathId"]
            if isinstance(header.get("name"), str):
                info["object_name"] = header["name"]
            if isinstance(header.get("sourceFile"), str):
                info["source_file"] = header["sourceFile"]
            if isinstance(header.get("scriptPathId"), int):
                info["script_path_id"] = header["scriptPathId"]
    if info["object_name"] is None:
        stem = name.split(".", 1)[0]
        match = re.match(r"^(.*)_p[0-9A-Fa-f]{16}$", stem)
        info["object_name"] = match.group(1) if match else stem
    return info


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------


class UnityObjectStore:
    """Read-only access to one export's ``game/Unity.sqlite``. Thread-safe."""

    _cache: dict[str, "UnityObjectStore"] = {}
    _cache_lock = threading.Lock()

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        if not self.path.is_file():
            raise UnityStoreError(
                f"no Unity object store at {self.path}; export the Unity stages, or pack a layout-v2 root with "
                "python -m scripts.game_data.extraction.pack_unity_store --export-root <root>"
            )
        self._local = threading.local()
        self._connections: list[sqlite3.Connection] = []
        self._connections_lock = threading.Lock()
        schema = self._connection().execute("SELECT value FROM meta WHERE key='schema'").fetchone()
        if not schema or schema[0] != STORE_SCHEMA:
            raise UnityStoreError(f"{self.path} declares schema {schema[0] if schema else None!r}; expected {STORE_SCHEMA!r}")

    @classmethod
    def for_export(cls, export_root: Path | None = None) -> "UnityObjectStore":
        """The store of an export root (default: the configured one), opened once per process."""
        layout = ExportLayout(export_root) if export_root is not None else ExportLayout.configured()
        path = layout.unity_store_path
        key = os.path.normcase(os.path.abspath(path))
        with cls._cache_lock:
            store = cls._cache.get(key)
            if store is None or not store.path.is_file():
                store = cls(path)
                cls._cache[key] = store
            return store

    @classmethod
    def clear_cache(cls) -> None:
        """Close and forget every cached store (Windows keeps an open file undeletable)."""
        with cls._cache_lock:
            stores = list(cls._cache.values())
            cls._cache.clear()
        for store in stores:
            store.close()

    def close(self) -> None:
        """Close the connections of every thread; the store reopens on next use."""
        with self._connections_lock:
            connections, self._connections = self._connections, []
        for connection in connections:
            connection.close()
        self._local = threading.local()

    def __enter__(self) -> "UnityObjectStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _connection(self) -> sqlite3.Connection:
        connection = getattr(self._local, "connection", None)
        if connection is None:
            uri = self.path.resolve().as_uri() + "?mode=ro"
            try:
                connection = sqlite3.connect(uri, uri=True, check_same_thread=False)
            except sqlite3.Error as exc:
                raise UnityStoreError(f"cannot open {self.path}: {exc}") from exc
            self._local.connection = connection
            with self._connections_lock:
                self._connections.append(connection)
        return connection

    # -- listing ------------------------------------------------------------
    def types(self) -> list[str]:
        return [row[0] for row in self._connection().execute("SELECT DISTINCT type FROM objects ORDER BY type")]

    def count(self, type_name: str | None = None) -> int:
        if type_name is None:
            return int(self._connection().execute("SELECT COUNT(*) FROM objects").fetchone()[0])
        return int(self._connection().execute("SELECT COUNT(*) FROM objects WHERE type=?", (type_name,)).fetchone()[0])

    def counts(self) -> dict[str, int]:
        return dict(self._connection().execute("SELECT type, COUNT(*) FROM objects GROUP BY type ORDER BY type"))

    def _select(self, columns: str, type_name: str, pattern: str | None) -> Iterator[tuple]:
        """Rows of one type whose file name matches a case-insensitive glob, by name."""
        pattern = pattern or "*"
        prefix = _glob_prefix(pattern)
        sql = f"SELECT {columns} FROM objects WHERE type=?"
        params: list[Any] = [type_name]
        if prefix:
            sql += " AND name LIKE ? ESCAPE '\\'"
            params.append(_like_escape(prefix) + "%")
        sql += " ORDER BY name"
        exact_match = pattern == prefix
        folded = pattern.casefold()
        for row in self._connection().execute(sql, params):
            name = row[1]
            if exact_match:
                if name.casefold() != folded:
                    continue
            elif pattern != "*" and not fnmatch.fnmatchcase(name.casefold(), folded):
                continue
            yield row

    def names(self, type_name: str, pattern: str | None = None) -> list[str]:
        return [row[1] for row in self._select("type, name", type_name, pattern)]

    def rows(self, type_name: str, pattern: str | None = None) -> list[UnityObjectRow]:
        return [UnityObjectRow(*row) for row in self._select(_ROW_COLUMNS, type_name, pattern)]

    def iter_rows(self, type_name: str | None = None) -> Iterator[UnityObjectRow]:
        """Every row (without document bytes), ordered by type and name, streamed.

        For whole-store walks such as audits and diffs: nothing is held in
        memory beyond the current row.
        """
        sql = f"SELECT {_ROW_COLUMNS} FROM objects"
        params: tuple[str, ...] = ()
        if type_name is not None:
            sql += " WHERE type=?"
            params = (type_name,)
        for found in self._connection().execute(sql + " ORDER BY type, name", params):
            yield UnityObjectRow(*found)

    def meta(self, key: str) -> str | None:
        found = self._connection().execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return found[0] if found else None

    def row(self, type_name: str, name: str) -> UnityObjectRow | None:
        found = self._connection().execute(
            f"SELECT {_ROW_COLUMNS} FROM objects WHERE type=? AND name=?", (type_name, name)
        ).fetchone()
        return UnityObjectRow(*found) if found else None

    def rows_by_object_name(self, type_name: str, object_name: str) -> list[UnityObjectRow]:
        return [
            UnityObjectRow(*row)
            for row in self._connection().execute(
                f"SELECT {_ROW_COLUMNS} FROM objects WHERE type=? AND object_name=? ORDER BY name",
                (type_name, object_name),
            )
        ]

    def rows_by_path_id(self, path_id: int, source_file: str | None = None) -> list[UnityObjectRow]:
        sql = f"SELECT {_ROW_COLUMNS} FROM objects WHERE path_id=?"
        params: list[Any] = [path_id]
        if source_file is not None:
            sql += " AND source_file=?"
            params.append(source_file)
        return [UnityObjectRow(*row) for row in self._connection().execute(sql + " ORDER BY type, name", params)]

    def exists(self, type_name: str, name: str) -> bool:
        return self._connection().execute(
            "SELECT 1 FROM objects WHERE type=? AND name=?", (type_name, name)
        ).fetchone() is not None

    # -- content ------------------------------------------------------------
    def read_bytes(self, type_name: str, name: str) -> bytes:
        found = self._connection().execute(
            "SELECT data FROM objects WHERE type=? AND name=?", (type_name, name)
        ).fetchone()
        if found is None:
            raise KeyError(logical_ref(type_name, name))
        return zlib.decompress(found[0])

    def read_text(self, type_name: str, name: str) -> str:
        return self.read_bytes(type_name, name).decode("utf-8-sig")

    def read_json(self, type_name: str, name: str, default: Any = _MISSING) -> Any:
        try:
            return json.loads(self.read_text(type_name, name))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
            if default is _MISSING:
                raise
            return default

    def iter_documents(
        self, type_name: str, pattern: str | None = None
    ) -> Iterator[tuple[UnityObjectRow, bytes]]:
        """Every matching row with its exact bytes, in name order, streamed."""
        for row in self._select(_ROW_COLUMNS + ", data", type_name, pattern):
            yield UnityObjectRow(*row[:-1]), zlib.decompress(row[-1])

    def iter_json(self, type_name: str, pattern: str | None = None) -> Iterator[tuple[UnityObjectRow, Any]]:
        """Every matching row with its parsed JSON; an unparsable document raises."""
        for row, data in self.iter_documents(type_name, pattern):
            yield row, json.loads(data.decode("utf-8-sig"))

    def read_ref(self, ref: str | os.PathLike[str]) -> bytes:
        """The bytes behind a ``game/Unity/<Type>/<name>`` reference."""
        parts = split_logical_ref(ref)
        if parts is None:
            raise KeyError(str(ref))
        return self.read_bytes(*parts)

    def export(self, type_name: str, pattern: str | None, out_dir: Path) -> int:
        """Write matching documents as loose files under ``out_dir/<Type>/`` for tools that need files."""
        target = Path(out_dir) / type_name
        target.mkdir(parents=True, exist_ok=True)
        written = 0
        for row, data in self.iter_documents(type_name, pattern):
            (target / row.name).write_bytes(data)
            written += 1
        return written


def open_store(export_root: Path | None = None) -> UnityObjectStore:
    """Shorthand for :meth:`UnityObjectStore.for_export`; a missing store raises UnityStoreError."""
    return UnityObjectStore.for_export(export_root)


def open_store_if_present(export_root: Path | None = None) -> UnityObjectStore | None:
    """The export's store, or None when the root has none (no Unity stage was exported).

    For consumers whose Unity input was already optional (they skipped a
    missing ``game/Unity/<Type>`` folder); a store that exists but is
    unreadable or another schema still raises.
    """
    layout = ExportLayout(export_root) if export_root is not None else ExportLayout.configured()
    if not layout.unity_store_path.is_file():
        return None
    return UnityObjectStore.for_export(layout.root)


def store_loose_documents(export_root: Path, *, jobs: int = 4) -> int:
    """Move every loose object document under game/Unity into the store; returns the count.

    Test fixtures and small hand-built roots write loose files and call this;
    it does not touch the layout marker. Real v2 roots use pack_unity_store.
    """
    layout = ExportLayout(export_root)
    moved = 0
    if not layout.unity_dir.is_dir():
        return moved
    with UnityObjectStoreWriter(layout.unity_store_path, jobs=jobs) as writer:
        for type_entry in sorted(os.scandir(layout.unity_dir), key=lambda entry: entry.name):
            if not type_entry.is_dir():
                continue
            files = {e.name: Path(e.path) for e in os.scandir(type_entry.path) if e.is_file() and is_store_file(e.name)}
            if not files:
                continue
            writer.sync_type(type_entry.name, files, remove_missing=False)
            for path in files.values():
                path.unlink()
            moved += len(files)
            if not any(os.scandir(type_entry.path)):
                os.rmdir(type_entry.path)
    return moved


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Prepared:
    name: str
    size: int
    mtime_ns: int
    sha256: str
    info: dict[str, Any]
    blob: bytes


def _read_shared(path: Path, attempts: int = 6) -> tuple[os.stat_result, bytes]:
    """Stat and read one file, retrying a transient Windows sharing violation.

    A scanner or indexer can hold a freshly written file open for a moment;
    the read is retried with backoff and fails with the path after that.
    """
    for attempt in range(attempts):
        try:
            return path.stat(), path.read_bytes()
        except PermissionError as exc:
            # ERROR_CRC (23): the disk cannot read the sectors back; retrying cannot help.
            if getattr(exc, "winerror", None) == 23 or attempt == attempts - 1:
                raise PermissionError(f"cannot read {path} after {attempts} attempts: {exc}") from exc
            time.sleep(0.05 * (2 ** attempt))
    raise AssertionError("unreachable")


@dataclass(frozen=True)
class UnreadableDocument:
    name: str
    path: str
    error: str


def _prepare_or_error(name: str, path: Path) -> "_Prepared | UnreadableDocument":
    try:
        return _prepare(name, path)
    except OSError as exc:
        return UnreadableDocument(name, str(path), f"{type(exc).__name__}: {exc}")


def _prepare(name: str, path: Path) -> _Prepared:
    stat, data = _read_shared(path)
    return _Prepared(
        name=name,
        size=len(data),
        mtime_ns=stat.st_mtime_ns,
        sha256=hashlib.sha256(data).hexdigest(),
        info=describe_document(name, data),
        blob=zlib.compress(data, ZLIB_LEVEL),
    )


class UnityObjectStoreWriter:
    """Create or update a store. One writer per file; not for concurrent use."""

    def __init__(self, path: Path, *, jobs: int = 8) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.jobs = max(1, int(jobs))
        self.unreadable: list[tuple[str, UnreadableDocument]] = []
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=NORMAL")
        self.connection.executescript(_SCHEMA_SQL)
        existing = self.connection.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
        if existing and existing[0] != STORE_SCHEMA:
            self.connection.close()
            raise UnityStoreError(f"{self.path} declares schema {existing[0]!r}; expected {STORE_SCHEMA!r}")
        self.connection.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('schema', ?)", (STORE_SCHEMA,))
        self.connection.commit()

    def __enter__(self) -> "UnityObjectStoreWriter":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def stamps(self, type_name: str) -> dict[str, tuple[int, int]]:
        """``{name: (size, mtime_ns)}`` of one type's rows, for incremental sync."""
        return {
            name: (size, mtime_ns)
            for name, size, mtime_ns in self.connection.execute(
                "SELECT name, size, mtime_ns FROM objects WHERE type=?", (type_name,)
            )
        }

    def put(self, type_name: str, name: str, data: bytes, *, mtime_ns: int = 0) -> None:
        """Insert or replace one document from bytes (fixtures and small writers)."""
        self._insert(type_name, [
            _Prepared(name, len(data), mtime_ns, hashlib.sha256(data).hexdigest(),
                      describe_document(name, data), zlib.compress(data, ZLIB_LEVEL))
        ])

    def _insert(self, type_name: str, prepared: Iterable[_Prepared]) -> None:
        self.connection.executemany(
            "INSERT INTO objects (type, name, object_name, path_id, source_file, script_path_id, size, mtime_ns, sha256, data) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (type, name) DO UPDATE SET object_name=excluded.object_name, path_id=excluded.path_id, "
            "source_file=excluded.source_file, script_path_id=excluded.script_path_id, size=excluded.size, "
            "mtime_ns=excluded.mtime_ns, sha256=excluded.sha256, data=excluded.data",
            (
                (type_name, item.name, item.info["object_name"], item.info["path_id"], item.info["source_file"],
                 item.info["script_path_id"], item.size, item.mtime_ns, item.sha256, item.blob)
                for item in prepared
            ),
        )

    def get_meta(self, key: str) -> str | None:
        found = self.connection.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return found[0] if found else None

    def set_meta(self, key: str, value: str) -> None:
        self.connection.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
        self.connection.commit()

    def delete(self, type_name: str, names: Iterable[str]) -> int:
        names = list(names)
        self.connection.executemany("DELETE FROM objects WHERE type=? AND name=?", ((type_name, name) for name in names))
        return len(names)

    def sync_type(
        self,
        type_name: str,
        files: Mapping[str, Path],
        *,
        remove_missing: bool = True,
        progress: Any = None,
        strict: bool = True,
    ) -> dict[str, int]:
        """Make one type's rows equal ``files`` ({name: path}); unchanged (size, mtime) rows are kept.

        Documents are read, hashed and compressed on a thread pool and written
        in batches, so a million-row publish is bounded by disk read speed. A
        file that cannot be read is not stored and is listed in
        ``self.unreadable``; with ``strict`` (the default) the call then raises
        UnityStoreError naming every such file of the type, and a caller that
        wants the full set across types (the v2 packer) passes ``strict=False``.
        """
        current = self.stamps(type_name)
        changed: list[tuple[str, Path]] = []
        unchanged = 0
        for name, path in files.items():
            stamp = current.pop(name, None)
            if stamp is not None:
                stat = path.stat()
                if stamp == (stat.st_size, stat.st_mtime_ns):
                    unchanged += 1
                    continue
            changed.append((name, Path(path)))
        removed = self.delete(type_name, current) if remove_missing else 0
        written = 0
        batch = 2000
        unreadable = 0
        with ThreadPoolExecutor(max_workers=self.jobs) as pool:
            for start in range(0, len(changed), batch):
                chunk = changed[start:start + batch]
                prepared = []
                for item in pool.map(lambda entry: _prepare_or_error(*entry), chunk):
                    if isinstance(item, UnreadableDocument):
                        self.unreadable.append((type_name, item))
                        unreadable += 1
                    else:
                        prepared.append(item)
                self._insert(type_name, prepared)
                self.connection.commit()
                written += len(chunk)
                if progress is not None:
                    progress(type_name, written, len(changed))
        self.connection.commit()
        if unreadable and strict:
            failed = [item for failed_type, item in self.unreadable if failed_type == type_name]
            raise UnityStoreError(
                f"{unreadable} {type_name} document(s) could not be read and were not stored: "
                + "; ".join(f"{item.path}: {item.error}" for item in failed[:5])
            )
        return {"written": written - unreadable, "unchanged": unchanged, "removed": removed, "unreadable": unreadable}

    def drop_type(self, type_name: str) -> int:
        cursor = self.connection.execute("DELETE FROM objects WHERE type=?", (type_name,))
        self.connection.commit()
        return cursor.rowcount

    def close(self) -> None:
        if self.connection is None:
            return
        self.connection.commit()
        # Leave one self-contained file: fold the WAL back and drop its sidecars,
        # so read-only openers need no -wal/-shm and a copy of the file is complete.
        self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.connection.execute("PRAGMA journal_mode=DELETE")
        self.connection.close()
        self.connection = None  # type: ignore[assignment]
        UnityObjectStore.clear_cache()


def verify_store(path: Path, *, jobs: int = 8) -> dict[str, Any]:
    """Decompress every row and compare its SHA256 and size; the first mismatches are reported."""
    store = UnityObjectStore(path)
    try:
        return _verify(store, jobs)
    finally:
        store.close()


def _verify(store: UnityObjectStore, jobs: int) -> dict[str, Any]:
    mismatches: list[str] = []
    checked = 0
    lock = threading.Lock()

    def check(type_name: str) -> None:
        nonlocal checked
        local = 0
        for row, data in store.iter_documents(type_name):
            local += 1
            if len(data) != row.size or hashlib.sha256(data).hexdigest() != row.sha256:
                with lock:
                    if len(mismatches) < 20:
                        mismatches.append(row.ref)
        with lock:
            checked += local

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        list(pool.map(check, store.types()))
    integrity = store._connection().execute("PRAGMA quick_check").fetchone()[0]
    return {"checked": checked, "mismatches": mismatches, "quickCheck": integrity, "ok": not mismatches and integrity == "ok"}


# ---------------------------------------------------------------------------
# Study CLI
# ---------------------------------------------------------------------------


def _study_connection(store: UnityObjectStore) -> sqlite3.Connection:
    connection = store._connection()

    def inflate(blob: bytes | None) -> str | None:
        return None if blob is None else zlib.decompress(blob).decode("utf-8-sig", errors="replace")

    def doc(blob: bytes | None, path: str) -> Any:
        text = inflate(blob)
        if text is None:
            return None
        row = connection.execute("SELECT json_extract(?, ?)", (text, path)).fetchone()
        return row[0] if row else None

    connection.create_function("inflate", 1, inflate, deterministic=True)
    connection.create_function("doc", 2, doc, deterministic=True)
    return connection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect an export's Unity object store (game/Unity.sqlite).")
    parser.add_argument("--export-root", type=Path, default=None, help="Default: the configured export root.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stats", help="Row count per Unity type.")
    ls = sub.add_parser("ls", help="List file names of one type matching a glob.")
    ls.add_argument("type")
    ls.add_argument("pattern", nargs="?", default="*")
    cat = sub.add_parser("cat", help="Print one document.")
    cat.add_argument("type")
    cat.add_argument("name")
    sql = sub.add_parser("sql", help="Run SQL; inflate(data) and doc(data, '$.path') are available.")
    sql.add_argument("query")
    extract = sub.add_parser("extract", help="Write matching documents as loose files.")
    extract.add_argument("type")
    extract.add_argument("pattern")
    extract.add_argument("--out", type=Path, required=True)
    verify = sub.add_parser("verify", help="Check every row against its SHA256.")
    verify.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args(argv)

    try:
        store = UnityObjectStore.for_export(args.export_root)
        if args.command == "stats":
            for type_name, count in store.counts().items():
                print(f"{type_name}\t{count}")
            lost = json.loads(store.meta(UNREADABLE_META_KEY) or "[]")
            if lost:
                print(f"unreadable at pack, not stored\t{len(lost)}")
            print(f"total\t{store.count()}\t{store.path.stat().st_size / 1e9:.2f} GB")
        elif args.command == "ls":
            for name in store.names(args.type, args.pattern):
                print(name)
        elif args.command == "cat":
            sys.stdout.write(store.read_text(args.type, args.name))
        elif args.command == "sql":
            cursor = _study_connection(store).execute(args.query)
            if cursor.description:
                print("\t".join(column[0] for column in cursor.description))
            for row in cursor:
                print("\t".join("" if value is None else str(value) for value in row))
        elif args.command == "extract":
            print(f"wrote {store.export(args.type, args.pattern, args.out)} file(s) under {args.out / args.type}")
        elif args.command == "verify":
            report = verify_store(store.path, jobs=args.jobs)
            print(json.dumps(report, indent=2))
            return 0 if report["ok"] else 1
    except (UnityStoreError, KeyError, sqlite3.Error) as exc:
        print(f"unity_store: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
