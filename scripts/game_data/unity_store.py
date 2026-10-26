"""The export's Unity object store: every exported Unity object document in one SQLite file.

AnimeStudio exports one file per Unity object. Layout v3 publishes the text
documents among them -- the ``.json`` object dumps and the ``.anim`` YAML clips,
well over a million files -- into ``game/Unity.sqlite`` instead of
``game/Unity/<Type>/``. Converted media (PNG, OBJ, ...) stays loose under
``game/Unity/<Type>/`` because the browser and external viewers open it by path.

Converted ``.fbx`` models are the exception. An Animator export embeds every
mesh it references, and the same character is exported once per cutscene
bundle that carries it, so the same mesh bytes repeat dozens of times across
files that are never byte-identical. An FBX row therefore stores its binary
node tree with every large property block (``FBX_CHUNK_MIN`` bytes or more:
vertex, index, normal, UV and skin arrays) cut out into the shared ``chunks``
table, keyed by SHA256 and stored once. The packed document (the
zlib-compressed remainder and where each chunk goes back) is itself a chunk
and the row holds only its SHA256, so identical exports are stored once. :meth:`UnityObjectStore.read_bytes`
rejoins them, so a reader still gets the exported file byte for byte, and
``serve.py`` answers the path as before.

Each row is one former file, keyed by its Unity type folder and its exported
file name, so ``game/Unity/<Type>/<name>`` stays the logical reference every
report and published record already uses. The stored bytes are the exported
bytes exactly (zlib-compressed), with their SHA256; nothing is re-serialized.
Indexed header columns (object name, PathID, source file, script PathID) answer the
common lookups without inflating a document, and ``serve.py`` answers a
``game/Unity/<Type>/<name>`` request from the store.

The store exists because loose files made every consumer pay for directory
enumeration and cold small-file reads: about 2.8 ms per MonoBehaviour cold,
against about 20 us per row scanned from SQLite. There is no loose fallback:
an older root fails ``ExportLayout.require()`` with the pack command
(``pack_export_stores``) in the error, and a writer refuses to publish into
one (``ExportLayout.require_schema``).

Readers use :class:`UnityObjectStore` (builders call
``UnityObjectStore.for_export(root)`` and query by type plus a file-name glob,
by object name, or by PathID); the exporter and the packer
(``pack_export_stores``) use :class:`UnityObjectStoreWriter`. The ``objects``
table (``type, name, object_name, path_id, source_file, script_path_id``, all
indexed) is readable by any SQLite client; only the document body needs
``zlib`` to inflate. For ad-hoc study, the CLI registers SQL
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
import bisect
import fnmatch
import hashlib
import io
import json
import os
import re
import sqlite3
import struct
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

from scripts.game_data.fbx_normalize import normalize_fbx
from scripts.source_paths import ExportLayout

STORE_SCHEMA = "endfield.unity-object-store.v1"
PACK_COMMAND = "python -m scripts.game_data.extraction.pack_export_stores"
STORE_FILE_NAME = "Unity.sqlite"
#: Exported suffixes that are object documents and live in the store. Every
#: other suffix is converted media and stays a loose file.
STORE_SUFFIXES: tuple[str, ...] = (".json", ".anim", ".fbx")
ZLIB_LEVEL = 6
#: An FBX property block at least this long is stored once in ``chunks``.
#: Smaller blocks (names, transforms, scalar properties) stay in the row:
#: sharing them saves little and costs a reference each.
FBX_CHUNK_MIN = 256
#: Prefix of a chunked FBX row. A plain row is a zlib stream, which starts with 0x78.
_FBX_PACKED_MAGIC = b"\x00EFXP1"
#: Prefix of a shared FBX row: the SHA256 of its packed document follows, and
#: the packed document itself is stored once in ``chunks`` under that key, so
#: exports that normalize to the same bytes keep a single copy.
_FBX_SHARED_MAGIC = b"\x00EFXS1"
_FBX_MAGIC = b"Kaydara FBX Binary  \x00"
_FBX_INSERT = struct.Struct("<Q32s")
#: meta key listing source documents the v2 packer could not read and the
#: caller accepted as lost (``pack_export_stores --accept-unreadable``).
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
CREATE INDEX IF NOT EXISTS objects_source_file ON objects (source_file, type);
CREATE INDEX IF NOT EXISTS objects_script ON objects (script_path_id) WHERE script_path_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS chunks (sha256 BLOB PRIMARY KEY, data BLOB NOT NULL) WITHOUT ROWID;
"""

_ROW_COLUMNS = "type, name, object_name, path_id, source_file, script_path_id, size, sha256, mtime_ns"


class UnityStoreError(RuntimeError):
    """The store is missing, unreadable, or not this schema."""


class _DocumentStream(io.RawIOBase):
    """Seekable virtual FBX without fetching property chunks being skipped.

    A structural inventory need not inflate every repeated vertex array. This
    checks all referenced chunk lengths, but does not authenticate skipped
    chunk contents against their digests; read_bytes remains the full reader.
    """

    def __init__(self, connection, blob, expected_size):
        super().__init__()
        self.connection = connection
        if blob.startswith(_FBX_SHARED_MAGIC):
            digest = blob[len(_FBX_SHARED_MAGIC):]
            row = connection.execute('SELECT data FROM chunks WHERE sha256=?', (digest,)).fetchone()
            if row is None:
                raise UnityStoreError('shared FBX document chunk is missing')
            blob = row[0]
        self.segments = []
        self.ends = []
        self.position = 0
        self.size = 0

        def append(length, source, offset=0):
            if length:
                self.segments.append((self.size, source, offset))
                self.size += length
                self.ends.append(self.size)

        if blob.startswith(_FBX_PACKED_MAGIC):
            inserts, start = _packed_inserts(blob)
            remainder = zlib.decompress(blob[start:])
            digests = list({digest for _, digest in inserts})
            lengths = {}
            for at in range(0, len(digests), 500):
                batch = digests[at:at+500]
                lengths.update(connection.execute(
                    f'SELECT sha256,length(data) FROM chunks WHERE sha256 IN ({",".join("?" for _ in batch)})', batch))
            cursor = 0
            for position, digest in inserts:
                if not cursor <= position <= len(remainder) or digest not in lengths:
                    raise UnityStoreError('FBX insert bounds differ or a property chunk is missing')
                append(position-cursor, remainder, cursor)
                append(lengths[digest], (digest,))
                cursor = position
            append(len(remainder)-cursor, remainder, cursor)
        else:
            data = zlib.decompress(blob)
            append(len(data), data)
        if self.size != expected_size:
            raise UnityStoreError(f'document stream length differs: {self.size}/{expected_size}')

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        self._checkClosed()
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        self._checkClosed()
        position = offset + (self.position if whence == io.SEEK_CUR else self.size if whence == io.SEEK_END else 0)
        if whence not in (io.SEEK_SET, io.SEEK_CUR, io.SEEK_END) or position < 0:
            raise ValueError('invalid document seek')
        self.position = position
        return position

    def readinto(self, buffer):
        self._checkClosed()
        count = min(len(buffer), max(0, self.size-self.position))
        copied = 0
        while copied < count:
            index = bisect.bisect_right(self.ends, self.position)
            start, source, offset = self.segments[index]
            take = min(count-copied, self.ends[index]-self.position)
            at = self.position-start+offset
            if isinstance(source, tuple):
                row = self.connection.execute('SELECT substr(data,?,?) FROM chunks WHERE sha256=?',
                    (at+1, take, source[0])).fetchone()
                if row is None or len(row[0]) != take:
                    raise UnityStoreError('FBX property chunk changed during structural read')
                data = row[0]
            else:
                data = source[at:at+take]
            buffer[copied:copied+take] = data
            copied += take
            self.position += take
        return copied


def is_store_file(name: str) -> bool:
    """True for an exported file name the store owns (an object document)."""
    return name.lower().endswith(STORE_SUFFIXES)


def store_path(export_root: Path) -> Path:
    return ExportLayout(export_root).unity_store_path


def logical_ref(type_name: str, name: str) -> str:
    """The ``game/Unity/<Type>/<name>`` reference a row stands for."""
    return f"game/Unity/{type_name}/{name}"


def _fbx_property_spans(data: bytes, minimum: int) -> list[tuple[int, int]] | None:
    """``(start, end)`` of every node property block of at least ``minimum`` bytes, in file order.

    Property blocks hold no file offsets (only node headers do), so cutting
    them out and putting them back leaves every header valid. None when the
    bytes are not a binary FBX whose node tree walks cleanly.
    """
    if not data.startswith(_FBX_MAGIC) or len(data) < 27:
        return None
    version = struct.unpack_from("<I", data, 23)[0]
    header = struct.Struct("<QQQ" if version >= 7500 else "<III")
    spans: list[tuple[int, int]] = []

    def walk(position: int, end: int) -> bool:
        while position + header.size <= end:
            node_end, _count, props_length = header.unpack_from(data, position)
            if node_end == 0:
                return True
            name_length = data[position + header.size]
            props_start = position + header.size + 1 + name_length
            props_end = props_start + props_length
            if not position < props_start <= props_end <= node_end <= end:
                return False
            if props_length >= minimum:
                spans.append((props_start, props_end))
            if node_end > props_end and not walk(props_end, node_end):
                return False
            position = node_end
        return True

    return spans if walk(27, len(data)) else None


def _encode_document(name: str, data: bytes) -> tuple[bytes, tuple[tuple[bytes, bytes], ...]]:
    """A row's ``data`` blob and the ``(sha256, bytes)`` chunks it references.

    A document is zlib-compressed. A binary FBX with large property blocks is
    stored as ``_FBX_PACKED_MAGIC``, the insert count, ``(position in the
    remainder, chunk SHA256)`` per block, then the zlib-compressed remainder.
    The blocks are already deflated arrays, so chunks are stored raw.
    """
    spans = _fbx_property_spans(data, FBX_CHUNK_MIN) if name.lower().endswith(".fbx") else None
    if not spans:
        return zlib.compress(data, ZLIB_LEVEL), ()
    remainder = bytearray()
    inserts = bytearray(struct.pack("<I", len(spans)))
    chunks: dict[bytes, bytes] = {}
    cursor = 0
    for start, end in spans:
        remainder += data[cursor:start]
        body = data[start:end]
        digest = hashlib.sha256(body).digest()
        chunks.setdefault(digest, body)
        inserts += _FBX_INSERT.pack(len(remainder), digest)
        cursor = end
    remainder += data[cursor:]
    blob = _FBX_PACKED_MAGIC + bytes(inserts) + zlib.compress(bytes(remainder), ZLIB_LEVEL)
    return _share_packed(blob, chunks)


def _share_packed(
    blob: bytes, chunks: dict[bytes, bytes] | None = None
) -> tuple[bytes, tuple[tuple[bytes, bytes], ...]]:
    """A shared row for a packed document, which joins its ``chunks`` after its own inserts."""
    digest = hashlib.sha256(blob).digest()
    items = dict(chunks or {})
    items[digest] = blob
    return _FBX_SHARED_MAGIC + digest, tuple(items.items())


def _packed_inserts(blob: bytes) -> tuple[list[tuple[int, bytes]], int]:
    """The ``(position, sha256)`` inserts of a chunked row and where its zlib remainder starts."""
    offset = len(_FBX_PACKED_MAGIC)
    count = struct.unpack_from("<I", blob, offset)[0]
    offset += 4
    inserts = [_FBX_INSERT.unpack_from(blob, offset + index * _FBX_INSERT.size) for index in range(count)]
    return inserts, offset + count * _FBX_INSERT.size


def _decode_document(connection: sqlite3.Connection, blob: bytes) -> bytes:
    """The exact document bytes of one row's ``data`` blob."""
    if blob.startswith(_FBX_SHARED_MAGIC):
        digest = bytes(blob[len(_FBX_SHARED_MAGIC):])
        found = connection.execute("SELECT data FROM chunks WHERE sha256 = ?", (digest,)).fetchone()
        if found is None:
            raise UnityStoreError("the packed FBX document a shared row references is missing from the store")
        blob = found[0]
    if not blob.startswith(_FBX_PACKED_MAGIC):
        return zlib.decompress(blob)
    inserts, remainder_start = _packed_inserts(blob)
    remainder = zlib.decompress(blob[remainder_start:])
    wanted = list({digest for _position, digest in inserts})
    bodies: dict[bytes, bytes] = {}
    for start in range(0, len(wanted), 500):
        batch = wanted[start:start + 500]
        bodies.update(connection.execute(
            f"SELECT sha256, data FROM chunks WHERE sha256 IN ({','.join('?' * len(batch))})", batch
        ).fetchall())
    missing = len(wanted) - len(bodies)
    if missing:
        raise UnityStoreError(f"{missing} FBX chunk(s) referenced by a row are missing from the store")
    parts: list[bytes] = []
    cursor = 0
    for position, digest in inserts:
        parts.append(remainder[cursor:position])
        parts.append(bodies[digest])
        cursor = position
    parts.append(remainder[cursor:])
    return b"".join(parts)


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

    def __init__(self, path: Path, *, schema: str = STORE_SCHEMA) -> None:
        """``schema`` lets another keyed document store reuse this engine
        (``game_file_store`` does); it is checked against the file's meta row."""
        self.path = Path(path)
        self.schema = schema
        if not self.path.is_file():
            raise UnityStoreError(
                f"no {schema} store at {self.path}; export the stages that produce it, or pack an older root with "
                f"{PACK_COMMAND} --export-root <root>"
            )
        self._local = threading.local()
        self._connections: list[sqlite3.Connection] = []
        self._connections_lock = threading.Lock()
        try:
            schema = self._connection().execute("SELECT value FROM meta WHERE key='schema'").fetchone()
            if not schema or schema[0] != self.schema:
                raise UnityStoreError(f"{self.path} declares schema {schema[0] if schema else None!r}; expected {self.schema!r}")
        except (sqlite3.Error, UnityStoreError):
            self.close()
            raise

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

    def iter_rows_by_script_path_id(
        self, script_path_id: int, type_name: str | None = None
    ) -> Iterator[UnityObjectRow]:
        """Rows referring to one MonoScript path ID, using the store's script index."""
        sql = f"SELECT {_ROW_COLUMNS} FROM objects WHERE script_path_id=?"
        params: list[Any] = [script_path_id]
        if type_name is not None:
            sql += " AND type=?"
            params.append(type_name)
        for found in self._connection().execute(sql + " ORDER BY type, name", params):
            yield UnityObjectRow(*found)

    def iter_rows_by_source_file(
        self, source_file: str, type_name: str | None = None
    ) -> Iterator[UnityObjectRow]:
        """Rows in one serialized source file, using the store's source index."""
        sql = f"SELECT {_ROW_COLUMNS} FROM objects WHERE source_file=?"
        params: list[Any] = [source_file]
        if type_name is not None:
            sql += " AND type=?"
            params.append(type_name)
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
        return _decode_document(self._connection(), found[0])

    def open_document(self, type_name: str, name: str) -> io.RawIOBase:
        """A read-only seekable document for bounded structural inventories.

        Close the returned stream before closing this store. Large skipped
        FBX properties are not fetched or hashed; this is not a full content
        integrity check. Document and referenced chunk lengths are checked.
        """
        connection = self._connection()
        found = connection.execute('SELECT data,size FROM objects WHERE type=? AND name=?',
                                   (type_name, name)).fetchone()
        if found is None:
            raise KeyError(logical_ref(type_name, name))
        # Read-ahead would fetch skipped array chunks when reading their node
        # headers. Structural callers deliberately read exact byte ranges.
        return _DocumentStream(connection, found[0], found[1])

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
        connection = self._connection()
        for row in self._select(_ROW_COLUMNS + ", data", type_name, pattern):
            yield UnityObjectRow(*row[:-1]), _decode_document(connection, row[-1])

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
    it does not touch the layout marker. Real older roots use pack_export_stores.
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
    chunks: tuple[tuple[bytes, bytes], ...] = ()


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
    return _prepare_bytes(name, data, stat.st_mtime_ns)


def _prepare_bytes(name: str, data: bytes, mtime_ns: int) -> _Prepared:
    if name.lower().endswith(".fbx"):
        # Same content, same bytes: drops the SDK's per-write stamps and ids,
        # so content-identical exports dedup by hash. Size is preserved.
        data = normalize_fbx(data)
    blob, chunks = _encode_document(name, data)
    return _Prepared(
        name=name,
        size=len(data),
        mtime_ns=mtime_ns,
        sha256=hashlib.sha256(data).hexdigest(),
        info=describe_document(name, data),
        blob=blob,
        chunks=chunks,
    )


class UnityObjectStoreWriter:
    """Create or update a store. One writer per file; not for concurrent use."""

    def __init__(self, path: Path, *, jobs: int = 8, schema: str = STORE_SCHEMA) -> None:
        self.path = Path(path)
        self.schema = schema
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.jobs = max(1, int(jobs))
        self.unreadable: list[tuple[str, UnreadableDocument]] = []
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=NORMAL")
        self.connection.executescript(_SCHEMA_SQL)
        existing = self.connection.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
        if existing and existing[0] != schema:
            self.connection.close()
            raise UnityStoreError(f"{self.path} declares schema {existing[0]!r}; expected {schema!r}")
        self.connection.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('schema', ?)", (schema,))
        self.connection.commit()
        # Set by any write that may orphan FBX chunks; close() then collects them.
        self._collect_chunks = False

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
        self._insert(type_name, [_prepare_bytes(name, data, mtime_ns)])

    def _insert(self, type_name: str, prepared: Iterable[_Prepared]) -> None:
        prepared = list(prepared)
        # Chunks first, so no committed row references a chunk that is not stored.
        self.connection.executemany(
            "INSERT OR IGNORE INTO chunks (sha256, data) VALUES (?, ?)",
            (chunk for item in prepared for chunk in item.chunks),
        )
        # A replaced chunked row can leave chunks nothing references.
        self._collect_chunks = True
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
        self._collect_chunks = True
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

    def merge_staged(
        self, type_name: str, staged: Iterable[Path], *, batch: int = 20000,
        remove_missing: bool = True,
    ) -> dict[str, int]:
        """Make one type's rows equal the union of that type's rows in ``staged`` stores, with SQL.

        ``staged`` are store files of this schema (AnimeStudio ``--document_store``
        output) in overlay order: on the same name (case-insensitive, like the
        ``name`` column) a later store wins. Rows are copied as stored -- bytes,
        hash and header columns -- so nothing is read back or recompressed. Only
        rows whose SHA256 differs from the current row are written, rows of the
        type absent from the union are deleted when ``remove_missing`` is true,
        and the counts match
        :meth:`sync_type` (``written``/``unchanged``/``removed``).
        """
        paths = [Path(path) for path in staged]
        if len(paths) > 8:
            raise UnityStoreError(f"merge_staged attaches at most 8 stores at once; got {len(paths)} for {type_name}")
        connection = self.connection
        connection.commit()
        aliases: list[str] = []
        try:
            for index, path in enumerate(paths):
                if not path.is_file():
                    raise UnityStoreError(f"staged store {path} does not exist")
                alias = f"staged{index}"
                connection.execute(f"ATTACH DATABASE ? AS {alias}", (str(path),))
                aliases.append(alias)
                found = connection.execute(f"SELECT value FROM {alias}.meta WHERE key='schema'").fetchone()
                if not found or found[0] != self.schema:
                    raise UnityStoreError(f"{path} declares schema {found[0] if found else None!r}; expected {self.schema!r}")
            connection.execute(
                "CREATE TEMP TABLE IF NOT EXISTS merge_pick ("
                "name TEXT PRIMARY KEY COLLATE NOCASE, src INTEGER NOT NULL, rid INTEGER NOT NULL, "
                "sha256 TEXT NOT NULL, unchanged INTEGER NOT NULL DEFAULT 0)"
            )
            connection.execute("CREATE INDEX IF NOT EXISTS temp.merge_pick_src ON merge_pick (src, rid)")
            connection.execute("DELETE FROM temp.merge_pick")
            for index, alias in enumerate(aliases):
                connection.execute(
                    f"INSERT INTO temp.merge_pick (name, src, rid, sha256) "
                    f"SELECT name, ?, rowid, sha256 FROM {alias}.objects WHERE type=? "
                    "ON CONFLICT (name) DO UPDATE SET src=excluded.src, rid=excluded.rid, sha256=excluded.sha256",
                    (index, type_name),
                )
            connection.execute(
                "UPDATE temp.merge_pick SET unchanged=1 WHERE EXISTS ("
                "SELECT 1 FROM main.objects m WHERE m.type=? AND m.name=merge_pick.name AND m.sha256=merge_pick.sha256)",
                (type_name,),
            )
            connection.commit()
            # Chunks before rows, as in _insert. Copying every staged chunk is
            # safe: one no row references is collected on close().
            self._collect_chunks = True
            for alias in aliases:
                has_chunks = connection.execute(
                    f"SELECT 1 FROM {alias}.sqlite_master WHERE type='table' AND name='chunks'"
                ).fetchone()
                if has_chunks:
                    connection.execute(f"INSERT OR IGNORE INTO main.chunks (sha256, data) SELECT sha256, data FROM {alias}.chunks")
            connection.commit()
            picked = connection.execute("SELECT COUNT(*) FROM temp.merge_pick").fetchone()[0]
            removed = 0
            if remove_missing:
                removed = connection.execute(
                    "DELETE FROM main.objects WHERE type=? AND name NOT IN (SELECT name FROM temp.merge_pick)",
                    (type_name,),
                ).rowcount
                connection.commit()
            written = 0
            for index, alias in enumerate(aliases):
                low, high = connection.execute(
                    "SELECT MIN(rid), MAX(rid) FROM temp.merge_pick WHERE src=? AND unchanged=0", (index,)
                ).fetchone()
                if low is None:
                    continue
                for start in range(low, high + 1, batch):
                    before = connection.total_changes
                    # The WHERE on the SELECT is what lets SQLite parse the upsert.
                    connection.execute(
                        "INSERT INTO main.objects (type, name, object_name, path_id, source_file, script_path_id, "
                        "size, mtime_ns, sha256, data) "
                        "SELECT o.type, p.name, o.object_name, o.path_id, o.source_file, o.script_path_id, "
                        f"o.size, o.mtime_ns, o.sha256, o.data FROM temp.merge_pick p JOIN {alias}.objects o "
                        "ON o.rowid = p.rid WHERE p.src=? AND p.unchanged=0 AND p.rid BETWEEN ? AND ? "
                        "ON CONFLICT (type, name) DO UPDATE SET object_name=excluded.object_name, "
                        "path_id=excluded.path_id, source_file=excluded.source_file, "
                        "script_path_id=excluded.script_path_id, size=excluded.size, mtime_ns=excluded.mtime_ns, "
                        "sha256=excluded.sha256, data=excluded.data WHERE excluded.sha256 <> objects.sha256",
                        (index, start, start + batch - 1),
                    )
                    written += connection.total_changes - before
                    connection.commit()
            connection.execute("DELETE FROM temp.merge_pick")
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            for alias in aliases:
                connection.execute(f"DETACH DATABASE {alias}")
        return {"written": written, "unchanged": int(picked) - written, "removed": removed, "unreadable": 0}

    def drop_type(self, type_name: str) -> int:
        cursor = self.connection.execute("DELETE FROM objects WHERE type=?", (type_name,))
        self.connection.commit()
        self._collect_chunks = True
        return cursor.rowcount

    def collect_chunks(self) -> int:
        """Delete FBX chunks no row references; returns how many were removed.

        Only ``.fbx`` rows are read, and of those only the insert header.
        """
        connection = self.connection
        if connection.execute("SELECT 1 FROM chunks LIMIT 1").fetchone() is None:
            return 0
        connection.execute("CREATE TEMP TABLE IF NOT EXISTS chunk_refs (sha256 BLOB PRIMARY KEY) WITHOUT ROWID")
        connection.execute("DELETE FROM temp.chunk_refs")
        def keep(digests: Any) -> None:
            connection.executemany("INSERT OR IGNORE INTO temp.chunk_refs (sha256) VALUES (?)", ((d,) for d in digests))

        head = len(_FBX_SHARED_MAGIC)
        shared = {
            bytes(blob[head:head + 32])
            for (blob,) in connection.execute(
                "SELECT data FROM objects WHERE name LIKE '%.fbx' AND substr(data, 1, ?) = ?", (head, _FBX_SHARED_MAGIC)
            )
        }
        keep(shared)
        # A packed document's inserts sit in its header; read only that much,
        # and re-read the rare header longer than the window in full.
        header = len(_FBX_PACKED_MAGIC) + 4 + _FBX_INSERT.size * 4096

        def keep_inserts(rows: Any, reread: str) -> None:
            for key, blob in rows:
                if len(blob) == header:
                    count = struct.unpack_from("<I", blob, len(_FBX_PACKED_MAGIC))[0]
                    needed = len(_FBX_PACKED_MAGIC) + 4 + count * _FBX_INSERT.size
                    if needed > header:
                        blob = connection.execute(reread, (needed, key)).fetchone()[0]
                inserts, _start = _packed_inserts(blob)
                keep(digest for _position, digest in inserts)

        keep_inserts(list(connection.execute(
            "SELECT rowid, substr(data, 1, ?) FROM objects WHERE name LIKE '%.fbx' AND substr(data, 1, ?) = ?",
            (header, len(_FBX_PACKED_MAGIC), _FBX_PACKED_MAGIC),
        )), "SELECT substr(data, 1, ?) FROM objects WHERE rowid = ?")
        wanted = list(shared)
        for start in range(0, len(wanted), 500):
            batch = wanted[start:start + 500]
            keep_inserts(list(connection.execute(
                f"SELECT sha256, substr(data, 1, ?) FROM chunks WHERE sha256 IN ({','.join('?' * len(batch))})",
                [header, *batch],
            )), "SELECT substr(data, 1, ?) FROM chunks WHERE sha256 = ?")
        removed = connection.execute(
            "DELETE FROM chunks WHERE sha256 NOT IN (SELECT sha256 FROM temp.chunk_refs)"
        ).rowcount
        connection.execute("DELETE FROM temp.chunk_refs")
        connection.commit()
        return removed

    def close(self) -> None:
        if self.connection is None:
            return
        self.connection.commit()
        if self._collect_chunks:
            self.collect_chunks()
        # Refresh planner statistics so lookups by PathID or CAB use their
        # indexes instead of scanning a whole type.
        self.connection.execute("PRAGMA optimize=0x10002")
        # Leave one self-contained file: fold the WAL back and drop its sidecars,
        # so read-only openers need no -wal/-shm and a copy of the file is complete.
        self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.connection.execute("PRAGMA journal_mode=DELETE")
        self.connection.close()
        self.connection = None  # type: ignore[assignment]
        UnityObjectStore.clear_cache()


def normalize_stored_fbx(path: Path, *, batch: int = 200, progress: Any = None) -> dict[str, int]:
    """Rewrite stored ``.fbx`` rows that predate :func:`normalize_fbx` or shared rows, in place.

    A row whose bytes are already normalized but whose packed document still
    sits in the row is moved into ``chunks`` without decoding it again.
    Resumable: rows already shared are skipped by their prefix alone.
    """
    changed = shared = 0
    head = len(_FBX_SHARED_MAGIC)
    with UnityObjectStoreWriter(Path(path)) as writer:
        # The reader must be closed before the writer's close switches the
        # journal mode, which needs the database to itself.
        reader = UnityObjectStore(Path(path))
        try:
            connection = reader._connection()
            targets = connection.execute(
                "SELECT type, name, mtime_ns FROM objects WHERE name LIKE '%.fbx' AND substr(data, 1, ?) != ? "
                "ORDER BY type, name",
                (head, _FBX_SHARED_MAGIC),
            ).fetchall()
            for start in range(0, len(targets), batch):
                pending: dict[str, list[_Prepared]] = {}
                moves: list[tuple[bytes, str, str]] = []
                for type_name, name, mtime_ns in targets[start:start + batch]:
                    blob = connection.execute(
                        "SELECT data FROM objects WHERE type=? AND name=?", (type_name, name)
                    ).fetchone()[0]
                    data = _decode_document(connection, blob)
                    if normalize_fbx(data) != data:
                        pending.setdefault(type_name, []).append(_prepare_bytes(name, data, mtime_ns))
                        continue
                    if not blob.startswith(_FBX_PACKED_MAGIC):
                        continue  # too small to chunk; a plain zlib row has nothing to share
                    row_blob, chunks = _share_packed(blob)
                    writer.connection.executemany("INSERT OR IGNORE INTO chunks (sha256, data) VALUES (?, ?)", chunks)
                    moves.append((row_blob, type_name, name))
                for type_name, prepared in pending.items():
                    writer._insert(type_name, prepared)
                    changed += len(prepared)
                writer.connection.executemany("UPDATE objects SET data=? WHERE type=? AND name=?", moves)
                shared += len(moves)
                writer.connection.commit()
                if progress:
                    progress(min(start + batch, len(targets)), len(targets))
        finally:
            reader.close()
    return {"fbx": len(targets), "rewritten": changed, "shared": shared}


def verify_store(path: Path, *, jobs: int = 8, schema: str = STORE_SCHEMA) -> dict[str, Any]:
    """Decompress every row and compare its SHA256 and size; the first mismatches are reported."""
    store = UnityObjectStore(path, schema=schema)
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
        return None if blob is None else _decode_document(connection, blob).decode("utf-8-sig", errors="replace")

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
    sub.add_parser("normalize-fbx", help="Make stored FBX deterministic (fbx_normalize) so equal content dedups.")
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
        elif args.command == "normalize-fbx":
            path = store.path
            store.close()
            report = normalize_stored_fbx(
                path, progress=lambda done, total: print(f"{done}/{total}", end="\r", file=sys.stderr, flush=True)
            )
            print(file=sys.stderr)
            print(json.dumps(report))
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
