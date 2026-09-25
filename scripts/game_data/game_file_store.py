"""The export's packed game files: every file under PACKED_GAME_DIRS in one SQLite file.

Some final VFS families are tens of thousands of small files with few readers
(``Json/LipSync`` alone is most of ``game/Json`` by count). Layout v4 keeps
the folders listed in ``scripts.source_paths.PACKED_GAME_DIRS`` in
``game/GameFiles.sqlite`` instead of on disk. Each row is one former file,
keyed by its game/-relative path (``Json/LipSync/Chinese/x.json``), holding the
exact bytes zlib-compressed with their SHA256, so ``game/<path>`` stays the
reference every report already uses.

The store reuses the Unity object store engine (``unity_store``) under its own
schema token: the engine's ``type`` column holds the packed folder and its
``name`` column the path inside it. Callers never see that mapping; they use
game/-relative paths.

Readers that walk or read game files should use :func:`read_game_file`,
:func:`game_file_exists` and :func:`iter_game_tree`, which answer a packed
path from the store and any other path from disk, so they need not know which
folders are packed. There is no fallback between the two: a packed path is
never read from disk.

    python -m scripts.game_data.game_file_store stats
    python -m scripts.game_data.game_file_store ls Json/LipSync "Chinese/*"
    python -m scripts.game_data.game_file_store extract Json/LipSync "English/*" --out tmp\\study\\lipsync
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator, Mapping

if __package__ in {None, ""}:
    raise SystemExit("Run as: python -m scripts.game_data.game_file_store")

from scripts.game_data.unity_store import (
    UNREADABLE_META_KEY,
    UnityObjectRow,
    UnityObjectStore,
    UnityObjectStoreWriter,
    UnityStoreError,
    verify_store,
)
from scripts.source_paths import PACKED_GAME_DIRS, ExportLayout, packed_game_dir

GAME_FILE_STORE_SCHEMA = "endfield.game-file-store.v1"


def _posix(path: str | os.PathLike[str]) -> str:
    return str(path).replace("\\", "/").strip("/")


def _split(game_path: str) -> tuple[str, str]:
    """``(packed folder, path inside it)``; raises KeyError for an unpacked path."""
    text = _posix(game_path)
    folder = packed_game_dir(text)
    if folder is None or len(text) <= len(folder) + 1:
        raise KeyError(f"game/{text} is not a file under {PACKED_GAME_DIRS}")
    return folder, text[len(folder) + 1:]


@dataclass(frozen=True)
class GameFileRow:
    path: str  # game/-relative, e.g. Json/LipSync/Chinese/x.json
    size: int
    sha256: str
    mtime_ns: int = 0

    @property
    def ref(self) -> str:
        return f"game/{self.path}"

    @property
    def name(self) -> str:
        return PurePosixPath(self.path).name

    @classmethod
    def _from_engine(cls, row: UnityObjectRow) -> "GameFileRow":
        return cls(f"{row.type}/{row.name}", row.size, row.sha256, row.mtime_ns)


class GameFileStore:
    """Read-only access to one export's ``game/GameFiles.sqlite``. Thread-safe."""

    _cache: dict[str, "GameFileStore"] = {}
    _cache_lock = threading.Lock()

    def __init__(self, path: Path) -> None:
        self._engine = UnityObjectStore(path, schema=GAME_FILE_STORE_SCHEMA)
        self.path = self._engine.path

    @classmethod
    def for_export(cls, export_root: Path | None = None) -> "GameFileStore":
        layout = ExportLayout(export_root) if export_root is not None else ExportLayout.configured()
        path = layout.game_file_store_path
        key = os.path.normcase(os.path.abspath(path))
        with cls._cache_lock:
            store = cls._cache.get(key)
            if store is None or not store.path.is_file():
                store = cls(path)
                cls._cache[key] = store
            return store

    @classmethod
    def clear_cache(cls) -> None:
        with cls._cache_lock:
            stores = list(cls._cache.values())
            cls._cache.clear()
        for store in stores:
            store.close()

    def close(self) -> None:
        self._engine.close()

    def __enter__(self) -> "GameFileStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def folders(self) -> list[str]:
        return self._engine.types()

    def count(self, folder: str | None = None) -> int:
        return self._engine.count(folder)

    def meta(self, key: str) -> str | None:
        return self._engine.meta(key)

    def row(self, game_path: str) -> GameFileRow | None:
        found = self._engine.row(*_split(game_path))
        return GameFileRow._from_engine(found) if found else None

    def exists(self, game_path: str) -> bool:
        return self._engine.exists(*_split(game_path))

    def read_bytes(self, game_path: str) -> bytes:
        folder, name = _split(game_path)
        try:
            return self._engine.read_bytes(folder, name)
        except KeyError:
            raise KeyError(f"game/{_posix(game_path)}") from None

    def iter_rows(self, folder: str | None = None) -> Iterator[GameFileRow]:
        """Every row (no bytes) of one packed folder, or of all, ordered by path, streamed."""
        for row in self._engine.iter_rows(folder):
            yield GameFileRow._from_engine(row)

    def rows(self, folder: str, pattern: str | None = None) -> list[GameFileRow]:
        """Rows of one packed folder whose path inside it matches a case-insensitive glob."""
        return [GameFileRow._from_engine(row) for row in self._engine.rows(folder, pattern)]

    def iter_files(self, folder: str, pattern: str | None = None) -> Iterator[tuple[GameFileRow, bytes]]:
        for row, data in self._engine.iter_documents(folder, pattern):
            yield GameFileRow._from_engine(row), data

    def export(self, folder: str, pattern: str | None, out_dir: Path) -> int:
        """Write matching files as loose files under ``out_dir/<folder>/`` for tools that need files."""
        written = 0
        for row, data in self.iter_files(folder, pattern):
            target = Path(out_dir).joinpath(*PurePosixPath(row.path).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            written += 1
        return written


def open_game_files_if_present(export_root: Path | None = None) -> GameFileStore | None:
    """The export's game-file store, or None when the root has none."""
    layout = ExportLayout(export_root) if export_root is not None else ExportLayout.configured()
    if not layout.game_file_store_path.is_file():
        return None
    return GameFileStore.for_export(layout.root)


class GameFileStoreWriter:
    """Create or update a game-file store. One writer per file."""

    def __init__(self, path: Path, *, jobs: int = 8) -> None:
        self._engine = UnityObjectStoreWriter(path, jobs=jobs, schema=GAME_FILE_STORE_SCHEMA)
        self.path = self._engine.path

    def __enter__(self) -> "GameFileStoreWriter":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def unreadable(self) -> list[dict[str, str]]:
        return [
            {"path": f"{folder}/{item.name}", "file": item.path, "error": item.error}
            for folder, item in self._engine.unreadable
        ]

    def sync_folder(
        self,
        folder: str,
        files: Mapping[str, Path],
        *,
        remove_missing: bool = True,
        progress: Callable[[str, int, int], None] | None = None,
        strict: bool = True,
    ) -> dict[str, int]:
        """Make one packed folder's rows equal ``files`` ({path inside the folder: file})."""
        if folder not in PACKED_GAME_DIRS:
            raise UnityStoreError(f"{folder!r} is not one of PACKED_GAME_DIRS {PACKED_GAME_DIRS}")
        return self._engine.sync_type(folder, dict(files), remove_missing=remove_missing, progress=progress, strict=strict)

    def row_stamp(self, game_path: str) -> tuple[int, int] | None:
        folder, name = _split(game_path)
        return self._engine.stamps(folder).get(name)

    def read_existing(self, game_path: str) -> bytes | None:
        """The bytes a path currently holds in this store, or None."""
        folder, name = _split(game_path)
        found = self._engine.connection.execute(
            "SELECT data FROM objects WHERE type=? AND name=?", (folder, name)
        ).fetchone()
        return None if found is None else zlib.decompress(found[0])

    def put(self, game_path: str, data: bytes, *, mtime_ns: int = 0) -> None:
        folder, name = _split(game_path)
        self._engine.put(folder, name, data, mtime_ns=mtime_ns)
        self._engine.connection.commit()

    def delete(self, game_path: str) -> None:
        folder, name = _split(game_path)
        self._engine.delete(folder, [name])
        self._engine.connection.commit()

    def get_meta(self, key: str) -> str | None:
        return self._engine.get_meta(key)

    def set_meta(self, key: str, value: str) -> None:
        self._engine.set_meta(key, value)

    def close(self) -> None:
        self._engine.close()
        GameFileStore.clear_cache()


def verify_game_file_store(path: Path, *, jobs: int = 8) -> dict[str, Any]:
    return verify_store(path, jobs=jobs, schema=GAME_FILE_STORE_SCHEMA)


def loose_packed_files(layout: ExportLayout) -> dict[str, dict[str, Path]]:
    """``{folder: {path inside it: file}}`` of every loose file under a packed folder."""
    found: dict[str, dict[str, Path]] = {}
    for folder in PACKED_GAME_DIRS:
        base = layout.game.joinpath(*folder.split("/"))
        if not base.is_dir():
            continue
        files: dict[str, Path] = {}
        for dirpath, _dirnames, filenames in os.walk(base):
            for filename in filenames:
                path = Path(dirpath) / filename
                files[path.relative_to(base).as_posix()] = path
        if files:
            found[folder] = files
    return found


# ---------------------------------------------------------------------------
# Path-level access for readers: packed paths from the store, others from disk
# ---------------------------------------------------------------------------


def _game_relative(layout: ExportLayout, path: str | os.PathLike[str]) -> str:
    """A game/-relative posix path from a game/-relative or absolute path under game/."""
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            return candidate.relative_to(layout.game).as_posix()
        except ValueError:
            try:
                return candidate.resolve().relative_to(layout.game.resolve()).as_posix()
            except ValueError as exc:
                raise ValueError(f"{path} is not under {layout.game}") from exc
    text = _posix(path)
    return text[len("game/"):] if text.startswith("game/") else text


def locate_game_folder(directory: Path) -> tuple[Path, str] | None:
    """``(export root, game/-relative folder)`` for a directory inside an export's game/.

    The export root is the nearest ancestor ``X`` of ``directory`` whose child
    ``game`` contains it and which carries a layout marker. None for any other
    directory, such as loose files written by ``extract``. A packed folder need
    not exist on disk for this to answer.
    """
    resolved = Path(directory).resolve()
    for candidate in (resolved, *resolved.parents):
        if candidate.name.casefold() != "game":
            continue
        layout = ExportLayout(candidate.parent)
        if layout.layout_file.is_file():
            folder = "" if resolved == candidate else resolved.relative_to(candidate).as_posix()
            return layout.root, folder
    return None


def packed_dirs_within(folder: str) -> list[str]:
    """The PACKED_GAME_DIRS a walk of the game/-relative ``folder`` reaches (all for game/ itself)."""
    key = _posix(folder).casefold()
    return [
        packed for packed in PACKED_GAME_DIRS
        if not key or packed.casefold() == key or packed.casefold().startswith(key + "/")
        or key.startswith(packed.casefold() + "/")
    ]


def read_game_file(export_root: Path | None, path: str | os.PathLike[str]) -> bytes:
    """The bytes of one game file: from the store when its folder is packed, else from disk.

    ``path`` is game/-relative or an absolute path under the root's game/.
    A missing file raises FileNotFoundError either way.
    """
    layout = ExportLayout(export_root) if export_root is not None else ExportLayout.configured()
    relative = _game_relative(layout, path)
    if packed_game_dir(relative) is None:
        return layout.game.joinpath(*relative.split("/")).read_bytes()
    store = open_game_files_if_present(layout.root)
    try:
        if store is None:
            raise KeyError(relative)
        return store.read_bytes(relative)
    except KeyError:
        raise FileNotFoundError(f"game/{relative} is not in {layout.game_file_store_path}") from None


def game_file_exists(export_root: Path | None, path: str | os.PathLike[str]) -> bool:
    layout = ExportLayout(export_root) if export_root is not None else ExportLayout.configured()
    relative = _game_relative(layout, path)
    if packed_game_dir(relative) is None:
        return layout.game.joinpath(*relative.split("/")).is_file()
    store = open_game_files_if_present(layout.root)
    return store is not None and store.exists(relative)


@dataclass(frozen=True)
class GameTreeEntry:
    """One file under a game/ folder, whether loose or packed."""

    path: str  # game/-relative
    size: int
    packed: bool
    _load: Callable[[], bytes]

    @property
    def ref(self) -> str:
        return f"game/{self.path}"

    @property
    def name(self) -> str:
        return PurePosixPath(self.path).name

    def read_bytes(self) -> bytes:
        return self._load()


def iter_game_tree(export_root: Path | None, folder: str) -> Iterator[GameTreeEntry]:
    """Every file under a game/-relative folder, loose and packed, sorted by path (casefolded).

    Loose files under a packed folder are not yielded: a packed folder is read
    only from the store. This is the walk to use instead of ``rglob`` over any
    folder that contains, or is inside, a packed folder.
    """
    layout = ExportLayout(export_root) if export_root is not None else ExportLayout.configured()
    base_rel = _posix(folder)
    base_key = base_rel.casefold()
    entries: list[GameTreeEntry] = []
    packed_here = packed_dirs_within(base_rel)
    base = layout.game.joinpath(*base_rel.split("/")) if base_rel else layout.game
    if base.is_dir() and packed_game_dir(base_rel) is None:
        skip = {layout.game.joinpath(*packed.split("/")).as_posix().casefold() for packed in packed_here}
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if (Path(dirpath) / d).as_posix().casefold() not in skip]
            for filename in filenames:
                full = Path(dirpath) / filename
                if base == layout.game and filename in (layout.unity_store_path.name, layout.game_file_store_path.name):
                    continue
                entries.append(GameTreeEntry(
                    full.relative_to(layout.game).as_posix(), full.stat().st_size, False, full.read_bytes,
                ))
    store = open_game_files_if_present(layout.root) if packed_here else None
    if store is not None:
        for packed in packed_here:
            for row in store.iter_rows(packed):
                if base_key and not (row.path.casefold() == base_key or row.path.casefold().startswith(base_key + "/")):
                    continue
                entries.append(GameTreeEntry(
                    row.path, row.size, True, (lambda path=row.path: store.read_bytes(path)),
                ))
    entries.sort(key=lambda entry: entry.path.casefold())
    return iter(entries)


def store_loose_packed_files(export_root: Path, *, jobs: int = 4) -> int:
    """Move every loose file under a packed folder into the store; returns the count.

    For test fixtures and hand-built roots; real older roots use pack_export_stores.
    """
    layout = ExportLayout(export_root)
    moved = 0
    loose = loose_packed_files(layout)
    if not loose:
        return moved
    with GameFileStoreWriter(layout.game_file_store_path, jobs=jobs) as writer:
        for folder, files in loose.items():
            writer.sync_folder(folder, files, remove_missing=False)
            for path in files.values():
                path.unlink()
            moved += len(files)
            _remove_empty_dirs(layout.game.joinpath(*folder.split("/")))
    return moved


def _remove_empty_dirs(base: Path) -> None:
    if not base.is_dir():
        return
    for dirpath, _dirnames, _filenames in os.walk(base, topdown=False):
        if not os.listdir(dirpath):
            os.rmdir(dirpath)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect an export's packed game files (game/GameFiles.sqlite).")
    parser.add_argument("--export-root", type=Path, default=None, help="Default: the configured export root.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stats", help="File count per packed folder.")
    ls = sub.add_parser("ls", help="List paths in one packed folder matching a glob.")
    ls.add_argument("folder")
    ls.add_argument("pattern", nargs="?", default="*")
    cat = sub.add_parser("cat", help="Write one file's bytes to stdout.")
    cat.add_argument("path", help="game/-relative, e.g. Json/LipSync/Chinese/x.json")
    extract = sub.add_parser("extract", help="Write matching files as loose files.")
    extract.add_argument("folder")
    extract.add_argument("pattern")
    extract.add_argument("--out", type=Path, required=True)
    verify = sub.add_parser("verify", help="Check every row against its SHA256.")
    verify.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args(argv)
    try:
        store = GameFileStore.for_export(args.export_root)
        if args.command == "stats":
            for folder in store.folders():
                print(f"{folder}\t{store.count(folder)}")
            lost = json.loads(store.meta(UNREADABLE_META_KEY) or "[]")
            if lost:
                print(f"unreadable at pack, not stored\t{len(lost)}")
            print(f"total\t{store.count()}\t{store.path.stat().st_size / 1e9:.2f} GB")
        elif args.command == "ls":
            for row in store.rows(args.folder, args.pattern):
                print(row.path)
        elif args.command == "cat":
            sys.stdout.buffer.write(store.read_bytes(args.path))
        elif args.command == "extract":
            print(f"wrote {store.export(args.folder, args.pattern, args.out)} file(s) under {args.out}")
        elif args.command == "verify":
            report = verify_game_file_store(store.path, jobs=args.jobs)
            print(json.dumps(report, indent=2))
            return 0 if report["ok"] else 1
    except (UnityStoreError, KeyError) as exc:
        print(f"game_file_store: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
