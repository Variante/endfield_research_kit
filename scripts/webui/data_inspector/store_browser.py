"""Read-only query API over an export's SQLite stores, for the WebUI Data page.

``serve.py`` routes ``/api/stores*`` here. The browser cannot open a
multi-gigabyte SQLite file itself, so the local server answers three bounded
questions and the Data page renders them:

* ``list_stores``: which stores an export root has, with per-group counts;
* ``query_rows``: a page of rows of one group (a Unity type, or a packed
  game folder), filtered by name, object name, PathID or CAB;
* ``run_sql``: one read-only SQL statement with ``inflate(data)`` and
  ``doc(data, '$.path')`` registered, a row cap and a time limit.

A row's bytes are not returned here: each row carries the ``/export_*`` URL
that ``serve.py`` already answers from the store, so the page fetches a
document the same way it fetches any exported file. Every connection is opened
read-only (``mode=ro`` plus ``PRAGMA query_only``) with an authorizer that
refuses ATTACH/DETACH and writes, so a query cannot touch anything but the
opened store.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
import zlib
from pathlib import Path
from typing import Any

from scripts.game_data.game_file_store import GAME_FILE_STORE_SCHEMA
from scripts.game_data.unity_store import STORE_SCHEMA as UNITY_STORE_SCHEMA
from scripts.game_data.unity_store import UNREADABLE_META_KEY
from scripts.source_paths import ExportLayout

STORE_UNITY = "unity"
STORE_GAME_FILES = "game-files"
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
    relative = f"Unity/{group}/{name}" if store == STORE_UNITY else f"{group}/{name}"
    if route == "/export_data":
        return f"/export_data/{relative}"
    return f"{route}/game/{relative}"


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
        })
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


def query_rows(
    export_root: Path,
    *,
    route: str,
    store: str,
    group: str,
    query: str = "",
    field: str = "name",
    offset: int = 0,
    limit: int = DEFAULT_ROW_LIMIT,
) -> dict[str, Any]:
    """One page of a group's rows, filtered by ``field``.

    ``field`` is ``name`` (a glob when the query has ``*``/``?``, else a
    case-insensitive substring), ``object`` (object name substring, Unity
    only), ``pathId`` (decimal or 16-digit hex, Unity only) or ``cab`` (the
    source CAB, Unity only).
    """
    layout = ExportLayout(export_root)
    if not group:
        raise StoreBrowserError("group is required")
    limit = max(1, min(int(limit), MAX_ROW_LIMIT))
    offset = max(0, int(offset))
    where = ["type = ?"]
    params: list[Any] = [group]
    query = query.strip()
    unity = store == STORE_UNITY
    if query:
        if field == "name":
            if "*" in query or "?" in query:
                where.append("lower(name) GLOB lower(?)")
                params.append(query)
            else:
                where.append("name LIKE ? ESCAPE '\\'")
                params.append("%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
        elif field == "object" and unity:
            where.append("object_name LIKE ? ESCAPE '\\'")
            params.append("%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
        elif field == "pathId" and unity:
            try:
                path_id = _signed64(query) if _HEX16.match(query) else int(query)
            except ValueError as exc:
                raise StoreBrowserError(f"not a PathID: {query!r}") from exc
            # "+type" keeps the planner off the (type, name) index, which would
            # scan a whole type; the (path_id, source_file) index is exact.
            where[0] = "+type = ?"
            where.append("path_id = ?")
            params.append(path_id)
        elif field == "cab" and unity:
            where[0] = "+type = ?"
            where.append("source_file = ?")
            params.append(query)
        else:
            raise StoreBrowserError(f"unsupported filter field {field!r} for store {store!r}")
    connection = _connect(_store_file(layout, store), store)
    try:
        clause = " AND ".join(where)
        total = connection.execute(f"SELECT COUNT(*) FROM objects WHERE {clause}", params).fetchone()[0]
        columns = "name, object_name, path_id, source_file, script_path_id, size, sha256"
        rows = connection.execute(
            f"SELECT {columns} FROM objects WHERE {clause} ORDER BY name LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
    finally:
        connection.close()
    out = []
    for name, object_name, path_id, source_file, script_path_id, size, sha256 in rows:
        ref = f"game/Unity/{group}/{name}" if unity else f"game/{group}/{name}"
        row: dict[str, Any] = {"name": name, "ref": ref, "size": size, "sha256": sha256,
                               "url": _row_url(route, store, group, name)}
        if unity:
            row.update({
                "objectName": object_name,
                "pathId": None if path_id is None else str(path_id),
                "pathIdHex": None if path_id is None else f"{path_id & ((1 << 64) - 1):016X}",
                "sourceFile": source_file,
                "scriptPathId": None if script_path_id is None else str(script_path_id),
            })
        out.append(row)
    return {"store": store, "group": group, "total": total, "offset": offset, "limit": limit, "rows": out}


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
