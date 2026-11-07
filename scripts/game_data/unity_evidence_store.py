"""Read native SQLite evidence rows using explicit database/relative references.

Only object documents live in these stores. Selection, provenance receipts and
bounded command logs remain ordinary build metadata. There is no packing pass.
"""
from __future__ import annotations

import hashlib
import sqlite3
import zlib
from functools import lru_cache
from io import BytesIO, TextIOWrapper
from pathlib import Path, PurePosixPath

from scripts.game_data.unity_store import UnityObjectStore, UnityStoreError


@lru_cache(maxsize=8)
def _store(path: Path) -> UnityObjectStore:
    try:
        return UnityObjectStore(path)
    except (UnityStoreError, sqlite3.Error) as error:
        raise ValueError(f"invalid native evidence store {path}: {error}") from error


class EvidencePath:
    """An explicit row reference below an immutable native evidence database."""

    def __init__(self, database: Path, relative: str):
        self.database = database
        self.relative = PurePosixPath(str(relative).replace(chr(92), "/"))
        if self.relative.is_absolute() or ".." in self.relative.parts or ":" in str(self.relative):
            raise ValueError("evidence row escapes its database")

    def __str__(self):
        return str(self.database / str(self.relative))

    def __hash__(self):
        return hash((self.database, self.relative))

    def __eq__(self, other):
        return isinstance(other, EvidencePath) and (self.database, self.relative) == (other.database, other.relative)

    def __lt__(self, other):
        return str(self) < str(other)

    def __truediv__(self, value):
        return EvidencePath(self.database, str(self.relative / str(value).replace(chr(92), "/")))

    @property
    def name(self):
        return self.relative.name

    @property
    def stem(self):
        return self.relative.stem

    @property
    def parent(self):
        return EvidencePath(self.database, str(self.relative.parent))

    def relative_to(self, other):
        if not isinstance(other, EvidencePath) or self.database != other.database:
            raise ValueError("evidence references belong to different databases")
        return Path(str(self.relative.relative_to(other.relative)))

    def with_suffix(self, suffix):
        return EvidencePath(self.database, str(self.relative.with_suffix(suffix)))

    def resolve(self):
        # Row identities are lexical. Resolving every row against NTFS defeats
        # direct storage and incorrectly treats logical entries as loose files.
        return self

    def stat(self):
        return self.database.stat()

    def read_bytes(self):
        try:
            return _store(self.database).read_verified_bytes(str(self.relative.parent), self.name)
        except (UnityStoreError, sqlite3.Error, zlib.error) as error:
            raise ValueError(f"invalid native evidence row {self}: {error}") from error

    def read_text(self, encoding="utf-8", errors=None):
        return self.read_bytes().decode(encoding, errors or "strict")

    def open(self, mode="r", encoding=None, errors=None):
        if mode not in ("r", "rb"):
            raise ValueError("native evidence stores are read-only")
        stream = BytesIO(self.read_bytes())
        return stream if mode == "rb" else TextIOWrapper(stream, encoding=encoding or "utf-8", errors=errors)

    def is_file(self):
        return _store(self.database).exists(str(self.relative.parent), self.name)

    def iterdir(self):
        yield from self.glob("*")

    def glob(self, pattern):
        prefix = str(self.relative).rstrip("/") + "/"
        for name in _store(self.database).iter_relative_names(str(self.relative)):
            relative = PurePosixPath(name[len(prefix):])
            if len(relative.parts) == len(PurePosixPath(pattern).parts) and relative.match(pattern):
                yield EvidencePath(self.database, name)

    def rglob(self, pattern):
        prefix = str(self.relative).rstrip("/") + "/"
        for name in _store(self.database).iter_relative_names(str(self.relative)):
            if PurePosixPath(name[len(prefix):]).match(pattern):
                yield EvidencePath(self.database, name)


def evidence_path(value):
    """Read explicit SQLite row references or legacy loose evidence paths."""
    if isinstance(value, EvidencePath):
        return value
    path = Path(value)
    for index in range(len(path.parts)-2, -1, -1):
        if path.parts[index].lower().endswith(".sqlite"):
            return EvidencePath(Path(*path.parts[:index + 1]), "/".join(path.parts[index + 1:]))
    return path


def evidence_roots(run: Path, *, stored: bool):
    if stored:
        database = run / "objects.sqlite"
        return EvidencePath(database, "json"), EvidencePath(database, "raw")
    return run / "json", run / "raw"


def native_store_args(run: Path):
    return ["--document_store", str(run / "objects.sqlite"), "--document_store_root", str(run)]


def snapshot_path(value):
    """Snapshot each database once, while row hashes authenticate its contents."""
    path = evidence_path(value)
    return path.database if isinstance(path, EvidencePath) else path


def storage_receipt(run: Path, name="objects.sqlite"):
    path = run / name
    before = path.stat()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("native evidence store changed during hashing")
    return dict(path=str(path), length=after.st_size, sha256=digest)


def validate_storage(run: Path, extraction: dict, name="objects.sqlite"):
    expected = extraction.get("storage")
    if expected != storage_receipt(run, name):
        raise ValueError("native evidence store path/length/SHA256 differs")
