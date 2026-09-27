"""Read-only query API over an export's SQLite stores, for the WebUI Data page.

``serve.py`` routes ``/api/stores*`` here. The browser cannot open a
multi-gigabyte SQLite file itself, so the local server answers three bounded
questions and the Data page renders them:

* ``list_stores``: which stores an export root has, with per-group counts;
* ``query_rows``: a page of rows of one or more groups (Unity types, or
  packed game folders; none means the whole store), filtered by name,
  object name, PathID or CAB;
* ``run_sql``: one read-only SQL statement with ``inflate(data)`` and
  ``doc(data, '$.path')`` registered, a row cap and a time limit.

Beside the two SQLite stores, the ``loose`` source lists the decoded files
that stay loose under ``game/`` -- tables, JsonData outside the packed
folders, Lua, Terrain, and the converted Unity classes no other page shows
(Shader, Font, TextAsset) -- so the Data page covers every decodable output.
Media other pages already show (``PAGE_MEDIA_FOLDERS``) are left out. The
``undecoded`` source lists ``raw/``: the final VFS files no reader decodes
(Streaming, DynamicStreaming, IV, ExtendData, IFixPatch, the bundle manifest),
flagged ``binary`` so the page shows their bytes. Neither has SQL; their rows
answer ``query_rows`` by name like a store's.

A row's bytes are not returned here: each row carries the ``/export_*`` URL
that ``serve.py`` already answers from the store, so the page fetches a
document the same way it fetches any exported file. Every connection is opened
read-only (``mode=ro`` plus ``PRAGMA query_only``) with an authorizer that
refuses ATTACH/DETACH and writes, so a query cannot touch anything but the
opened store.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import sqlite3
import threading
import time
import zlib
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

from scripts.game_data.game_file_store import GAME_FILE_STORE_SCHEMA
from scripts.game_data.unity_store import STORE_SCHEMA as UNITY_STORE_SCHEMA
from scripts.game_data.unity_store import UNREADABLE_META_KEY
from scripts.source_paths import PACKED_GAME_DIRS, ExportLayout

STORE_UNITY = "unity"
STORE_GAME_FILES = "game-files"
STORE_LOOSE = "loose"
STORE_UNDECODED = "undecoded"
FILE_SOURCES = (STORE_LOOSE, STORE_UNDECODED)
#: game/ folders other pages show as media: the Assets page's videos, images,
#: sprites, models and FBX, and the Audio page's decoded audio. It mirrors
#: `scripts.webui.pages.PAGE_MEDIA`, the same media on the extraction side.
PAGE_MEDIA_FOLDERS = frozenset({
    "Audio", "Video", "Unity/Texture2D", "Unity/Sprite", "Unity/Mesh", "Unity/Animator",
})
#: A loose-file index is rebuilt when the export's layout marker changes, and
#: at least this often, since a changed-only refresh edits files in place.
LOOSE_INDEX_MAX_AGE_SECONDS = 60.0
DEFAULT_ROW_LIMIT = 200
MAX_ROW_LIMIT = 1000
SQL_ROW_LIMIT = 500
SQL_TIME_LIMIT_SECONDS = 15.0
SQL_CELL_TEXT_LIMIT = 4000
_HEX16 = re.compile(r"^(?:0x)?[0-9A-Fa-f]{16}$")


class StoreBrowserError(ValueError):
    """A request the API refuses; ``serve.py`` answers it with HTTP 400."""


def _store_file(layout: ExportLayout, store: str) -> Path:
    if store == STORE_UNITY:
        return layout.unity_store_path
    if store == STORE_GAME_FILES:
        return layout.game_file_store_path
    if store in FILE_SOURCES:
        raise StoreBrowserError(f"{store} files are not a SQLite store; SQL runs over the Unity or game-file store")
    raise StoreBrowserError(f"unknown store {store!r}; expected {STORE_UNITY!r} or {STORE_GAME_FILES!r}")


def _expected_schema(store: str) -> str:
    return UNITY_STORE_SCHEMA if store == STORE_UNITY else GAME_FILE_STORE_SCHEMA


def _deny_writes(action: int, *_args: Any) -> int:
    if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH) or action in _WRITE_ACTIONS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


_WRITE_ACTIONS = {
    getattr(sqlite3, name)
    for name in (
        "SQLITE_INSERT", "SQLITE_UPDATE", "SQLITE_DELETE", "SQLITE_CREATE_TABLE", "SQLITE_CREATE_INDEX",
        "SQLITE_CREATE_VIEW", "SQLITE_CREATE_TRIGGER", "SQLITE_DROP_TABLE", "SQLITE_DROP_INDEX",
        "SQLITE_DROP_VIEW", "SQLITE_DROP_TRIGGER", "SQLITE_ALTER_TABLE", "SQLITE_REINDEX",
        "SQLITE_ANALYZE", "SQLITE_CREATE_TEMP_TABLE", "SQLITE_CREATE_TEMP_INDEX", "SQLITE_CREATE_TEMP_VIEW",
        "SQLITE_CREATE_TEMP_TRIGGER", "SQLITE_DROP_TEMP_TABLE", "SQLITE_DROP_TEMP_INDEX",
        "SQLITE_DROP_TEMP_VIEW", "SQLITE_DROP_TEMP_TRIGGER", "SQLITE_TRANSACTION", "SQLITE_SAVEPOINT",
    )
    if hasattr(sqlite3, name)
}


def _connect(path: Path, store: str) -> sqlite3.Connection:
    if not path.is_file():
        raise StoreBrowserError(f"this export has no {path.name}")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, check_same_thread=False)
    connection.execute("PRAGMA query_only=1")
    schema = connection.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
    if not schema or schema[0] != _expected_schema(store):
        connection.close()
        raise StoreBrowserError(f"{path.name} declares schema {schema[0] if schema else None!r}")

    def inflate(blob: bytes | None) -> str | None:
        return None if blob is None else zlib.decompress(blob).decode("utf-8-sig", errors="replace")

    def doc(blob: bytes | None, json_path: str) -> Any:
        text = inflate(blob)
        if text is None:
            return None
        row = connection.execute("SELECT json_extract(?, ?)", (text, json_path)).fetchone()
        return row[0] if row else None

    connection.create_function("inflate", 1, inflate, deterministic=True)
    connection.create_function("doc", 2, doc, deterministic=True)
    connection.set_authorizer(_deny_writes)
    return connection


def _row_url(route: str, store: str, group: str, name: str) -> str:
    """The ``/export_*`` URL serve.py answers this row's bytes at."""
    if store == STORE_UNDECODED:
        # raw/ sits beside game/; /export_data serves only game/.
        return f"{'/export_full' if route == '/export_data' else route}/raw/{group}/{name}"
    relative = f"Unity/{group}/{name}" if store == STORE_UNITY else f"{group}/{name}"
    if route == "/export_data":
        return f"/export_data/{relative}"
    return f"{route}/game/{relative}"


_loose_lock = threading.Lock()
_loose_cache: dict[tuple[str, str], tuple[tuple[Any, ...], float, list[tuple[str, str, int]]]] = {}


def _loose_groups(game: Path) -> list[tuple[str, Path]]:
    """Each loose data folder under game/ as (group, path): top folders and Unity/<Type>."""
    groups: list[tuple[str, Path]] = []
    for entry in sorted(game.iterdir(), key=lambda item: item.name.lower()) if game.is_dir() else ():
        if not entry.is_dir():
            continue
        if entry.name == "Unity":
            for type_dir in sorted(entry.iterdir(), key=lambda item: item.name.lower()):
                if type_dir.is_dir() and f"Unity/{type_dir.name}" not in PAGE_MEDIA_FOLDERS:
                    groups.append((f"Unity/{type_dir.name}", type_dir))
        elif entry.name not in PAGE_MEDIA_FOLDERS:
            groups.append((entry.name, entry))
    return groups


def _raw_groups(raw: Path) -> list[tuple[str, Path]]:
    """Each undecoded block folder under raw/."""
    if not raw.is_dir():
        return []
    return [(entry.name, entry) for entry in sorted(raw.iterdir(), key=lambda item: item.name.lower()) if entry.is_dir()]


def loose_file_index(export_root: Path, source: str = STORE_LOOSE) -> list[tuple[str, str, int]]:
    """Every file of a file source as (group, path inside the group, size), sorted.

    ``loose`` walks game/ outside the stores and other pages' media; packed
    folders are rows of game/GameFiles.sqlite, never loose files, so they are
    skipped even if a stray copy is on disk. ``undecoded`` walks raw/.
    """
    layout = ExportLayout(export_root)
    base = layout.game if source == STORE_LOOSE else layout.raw
    try:
        marker = layout.layout_file.stat()
        stamp: tuple[Any, ...] = (marker.st_mtime_ns, marker.st_size)
    except OSError:
        stamp = (None, None)
    key = (source, os.path.normcase(str(base.resolve())))
    now = time.monotonic()
    with _loose_lock:
        cached = _loose_cache.get(key)
        if cached and cached[0] == stamp and now - cached[1] < LOOSE_INDEX_MAX_AGE_SECONDS:
            return cached[2]
    packed = {os.path.normcase(str(base.joinpath(*folder.split("/")))) for folder in PACKED_GAME_DIRS}
    groups = _loose_groups(base) if source == STORE_LOOSE else _raw_groups(base)
    rows: list[tuple[str, str, int]] = []
    for group, folder in groups:
        for dirpath, dirnames, filenames in os.walk(folder):
            dirnames[:] = sorted(
                name for name in dirnames if os.path.normcase(os.path.join(dirpath, name)) not in packed
            )
            relative_dir = Path(dirpath).relative_to(folder).as_posix()
            for filename in sorted(filenames):
                path = os.path.join(dirpath, filename)
                try:
                    size = os.stat(path).st_size
                except OSError:
                    continue
                name = filename if relative_dir == "." else f"{relative_dir}/{filename}"
                rows.append((group, name, size))
    rows.sort(key=lambda row: (row[0], row[1]))
    with _loose_lock:
        _loose_cache[key] = (stamp, now, rows)
    return rows


def _file_source_entry(export_root: Path, source: str) -> dict[str, Any] | None:
    rows = loose_file_index(export_root, source)
    if not rows:
        return None
    counts: dict[str, int] = {}
    for group, _name, _size in rows:
        counts[group] = counts.get(group, 0) + 1
    return {
        "id": source,
        "file": "game/" if source == STORE_LOOSE else "raw/",
        "bytes": sum(size for _group, _name, size in rows),
        "groups": [{"name": name, "count": count} for name, count in counts.items()],
        "rows": len(rows),
        "unreadableAtPack": [],
        "sql": False,
    }


def _query_loose(
    export_root: Path, *, route: str, source: str, groups: list[str], query: str, field: str, offset: int, limit: int,
) -> dict[str, Any]:
    if query and field != "name":
        raise StoreBrowserError(f"unsupported filter field {field!r} for store {source!r}")
    selected = set(groups)
    needle = query.lower()
    glob = "*" in query or "?" in query
    matched = [
        row for row in loose_file_index(export_root, source)
        if (not selected or row[0] in selected)
        and (not needle or (fnmatch.fnmatchcase(row[1].lower(), needle) if glob else needle in row[1].lower()))
    ]
    top = "game" if source == STORE_LOOSE else "raw"
    out = [
        {
            "group": group,
            "name": name,
            "ref": f"{top}/{group}/{name}",
            "size": size,
            "sha256": None,
            "url": _row_url(route, source, group, quote(name, safe="/")),
            **({"binary": True} if source == STORE_UNDECODED else {}),
        }
        for group, name, size in matched[offset:offset + limit]
    ]
    return {"store": source, "groups": groups, "total": len(matched), "offset": offset, "limit": limit,
            "rows": out}


def list_stores(export_root: Path, *, route: str) -> dict[str, Any]:
    """Every store of one export root with its groups and row counts."""
    layout = ExportLayout(export_root)
    stores: list[dict[str, Any]] = []
    for store in (STORE_UNITY, STORE_GAME_FILES):
        path = _store_file(layout, store)
        if not path.is_file():
            continue
        connection = _connect(path, store)
        try:
            groups = [
                {"name": name, "count": count}
                for name, count in connection.execute("SELECT type, COUNT(*) FROM objects GROUP BY type ORDER BY type")
            ]
            lost = connection.execute("SELECT value FROM meta WHERE key=?", (UNREADABLE_META_KEY,)).fetchone()
        finally:
            connection.close()
        stores.append({
            "id": store,
            "file": f"game/{path.name}",
            "bytes": path.stat().st_size,
            "groups": groups,
            "rows": sum(group["count"] for group in groups),
            "unreadableAtPack": json.loads(lost[0]) if lost else [],
            "sql": True,
        })
    for source in FILE_SOURCES:
        entry = _file_source_entry(export_root, source)
        if entry is not None:
            stores.append(entry)
    marker = layout.read_marker() or {}
    return {
        "root": layout.root.name,
        "route": route,
        "layout": marker.get("schema"),
        "state": marker.get("state"),
        "stores": stores,
    }


def _signed64(text: str) -> int:
    value = int(text[2:] if text.lower().startswith("0x") else text, 16)
    return value - (1 << 64) if value >= (1 << 63) else value


def _like_substring(text: str) -> str:
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _normalize_groups(group: str | Iterable[str] | None) -> list[str]:
    """One group, several, or none (the whole store), de-duplicated in order."""
    if group is None:
        return []
    values = [group] if isinstance(group, str) else list(group)
    seen: dict[str, None] = {}
    for value in values:
        if not isinstance(value, str):
            raise StoreBrowserError(f"group must be text, not {type(value).__name__}")
        if value:
            seen.setdefault(value, None)
    return list(seen)


def query_rows(
    export_root: Path,
    *,
    route: str,
    store: str,
    group: str | Iterable[str] | None = None,
    query: str = "",
    field: str = "name",
    offset: int = 0,
    limit: int = DEFAULT_ROW_LIMIT,
) -> dict[str, Any]:
    """One page of rows of the selected groups, filtered by ``field``.

    ``group`` is one group (a Unity type, or a packed game folder), several,
    or empty for every group of the store. Rows are ordered by ``type, name``
    and each carries its ``group``; ``total`` counts the whole selection.

    ``field`` is ``name`` (a glob when the query has ``*``/``?``, else a
    case-insensitive substring), ``object`` (object name substring, Unity
    only), ``pathId`` (decimal or 16-digit hex, Unity only) or ``cab`` (the
    source CAB, Unity only).
    """
    layout = ExportLayout(export_root)
    groups = _normalize_groups(group)
    limit = max(1, min(int(limit), MAX_ROW_LIMIT))
    offset = max(0, int(offset))
    if store in FILE_SOURCES:
        return _query_loose(
            export_root, route=route, source=store, groups=groups, query=query.strip(), field=field,
            offset=offset, limit=limit,
        )
    where: list[str] = []
    params: list[Any] = []
    # "+type" keeps the planner off the (type, name) index for the PathID and
    # CAB filters, which would scan whole types; their own indexes are exact.
    type_column = "type"
    query = query.strip()
    unity = store == STORE_UNITY
    if query:
        if field == "name":
            if "*" in query or "?" in query:
                where.append("lower(name) GLOB lower(?)")
                params.append(query)
            else:
                where.append("name LIKE ? ESCAPE '\\'")
                params.append(_like_substring(query))
        elif field == "object" and unity:
            where.append("object_name LIKE ? ESCAPE '\\'")
            params.append(_like_substring(query))
        elif field == "pathId" and unity:
            try:
                path_id = _signed64(query) if _HEX16.match(query) else int(query)
            except ValueError as exc:
                raise StoreBrowserError(f"not a PathID: {query!r}") from exc
            type_column = "+type"
            where.append("path_id = ?")
            params.append(path_id)
        elif field == "cab" and unity:
            type_column = "+type"
            where.append("source_file = ?")
            params.append(query)
        else:
            raise StoreBrowserError(f"unsupported filter field {field!r} for store {store!r}")
    if groups:
        where.insert(0, f"{type_column} IN ({', '.join('?' * len(groups))})")
        params[0:0] = groups
    connection = _connect(_store_file(layout, store), store)
    try:
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        total = connection.execute(f"SELECT COUNT(*) FROM objects {clause}", params).fetchone()[0]
        columns = "type, name, object_name, path_id, source_file, script_path_id, size, sha256"
        rows = connection.execute(
            f"SELECT {columns} FROM objects {clause} ORDER BY type, name LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
    finally:
        connection.close()
    out = []
    for row_group, name, object_name, path_id, source_file, script_path_id, size, sha256 in rows:
        ref = f"game/Unity/{row_group}/{name}" if unity else f"game/{row_group}/{name}"
        row: dict[str, Any] = {"group": row_group, "name": name, "ref": ref, "size": size, "sha256": sha256,
                               "url": _row_url(route, store, row_group, name)}
        if unity:
            row.update({
                "objectName": object_name,
                "pathId": None if path_id is None else str(path_id),
                "pathIdHex": None if path_id is None else f"{path_id & ((1 << 64) - 1):016X}",
                "sourceFile": source_file,
                "scriptPathId": None if script_path_id is None else str(script_path_id),
            })
        out.append(row)
    return {"store": store, "groups": groups, "total": total, "offset": offset, "limit": limit, "rows": out}


def _cell(value: Any) -> Any:
    if isinstance(value, bytes):
        return f"<blob {len(value)} bytes>"
    if isinstance(value, int) and not -(2 ** 53) <= value <= 2 ** 53:
        return str(value)  # JavaScript numbers lose 64-bit PathIDs
    if isinstance(value, str) and len(value) > SQL_CELL_TEXT_LIMIT:
        return value[:SQL_CELL_TEXT_LIMIT] + f"... [{len(value) - SQL_CELL_TEXT_LIMIT} more characters]"
    return value


def run_sql(
    export_root: Path,
    *,
    store: str,
    sql: str,
    limit: int = SQL_ROW_LIMIT,
    time_limit: float = SQL_TIME_LIMIT_SECONDS,
) -> dict[str, Any]:
    """Run one read-only statement; at most ``limit`` rows, aborted after ``time_limit`` seconds."""
    layout = ExportLayout(export_root)
    statement = sql.strip().rstrip(";").strip()
    if not statement:
        raise StoreBrowserError("empty query")
    limit = max(1, min(int(limit), SQL_ROW_LIMIT))
    connection = _connect(_store_file(layout, store), store)
    deadline = time.monotonic() + time_limit
    connection.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10000)
    started = time.monotonic()
    try:
        cursor = connection.execute(statement)
        columns = [column[0] for column in cursor.description or ()]
        rows = cursor.fetchmany(limit + 1)
    except sqlite3.OperationalError as exc:
        if "interrupted" in str(exc):
            raise StoreBrowserError(f"query stopped after {time_limit:.0f} s; narrow it with WHERE type=... or LIMIT") from exc
        raise StoreBrowserError(f"SQL error: {exc}") from exc
    except (sqlite3.DatabaseError, sqlite3.Warning) as exc:
        raise StoreBrowserError(f"SQL error: {exc}") from exc
    finally:
        connection.close()
    return {
        "store": store,
        "columns": columns,
        "rows": [[_cell(value) for value in row] for row in rows[:limit]],
        "truncated": len(rows) > limit,
        "limit": limit,
        "elapsedMs": round((time.monotonic() - started) * 1000),
    }
