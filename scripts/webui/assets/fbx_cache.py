"""Disposable FBX metadata cache keyed by exported bytes and reader code.

Stored objects supply their authoritative content digest, as for Assets' full
file hashes. Loose files are hashed from current bytes. A cache miss always
uses the ordinary readers; neither timestamps nor file names prove freshness.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sqlite3
import struct

from scripts.game_data import fbx_normalize
from scripts.webui.assets import fbx_root


_HASH = re.compile(r"[0-9a-f]{64}\Z")


class FbxMetadataCache:
    def __init__(self, path: Path):
        digest = hashlib.sha256(b'endfield.fbx-metadata-cache.v1\0')
        for source in (Path(__file__), Path(fbx_normalize.__file__), Path(fbx_root.__file__)):
            raw = source.read_bytes()
            digest.update(len(raw).to_bytes(8, 'little'))
            digest.update(raw)
        self.algorithm = digest.hexdigest()
        self.path = path
        self.connection = None
        self.hits = self.misses = 0

    def __enter__(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.path, timeout=0.2, isolation_level=None)
            self.connection.execute('PRAGMA journal_mode=WAL')
            self.connection.execute('PRAGMA synchronous=NORMAL')
            self.connection.execute('''CREATE TABLE IF NOT EXISTS fingerprints (
                algorithm TEXT, content TEXT, stem TEXT, fc TEXT, fv TEXT, root TEXT,
                PRIMARY KEY(algorithm, content, stem)) WITHOUT ROWID''')
        except (OSError, sqlite3.Error):
            self.close()
        return self

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __exit__(self, *exc):
        self.close()

    def get(self, content: str, stem: str):
        if self.connection is not None and _HASH.fullmatch(content.lower()):
            try:
                row = self.connection.execute(
                    'SELECT fc, fv, root FROM fingerprints WHERE algorithm=? AND content=? AND stem=?',
                    (self.algorithm, content.lower(), stem)).fetchone()
                if (row is not None and all(isinstance(value, str) for value in row)
                        and ((row[0] == row[1] == '') or
                             (_HASH.fullmatch(row[0]) and _HASH.fullmatch(row[1])))):
                    self.hits += 1
                    return row
            except sqlite3.Error:
                self.close()
        self.misses += 1
        return None

    def put(self, content: str, stem: str, result: tuple[str, str, str]):
        if self.connection is not None:
            try:
                self.connection.execute('INSERT OR REPLACE INTO fingerprints VALUES (?,?,?,?,?,?)',
                                        (self.algorithm, content.lower(), stem, *result))
            except sqlite3.Error:
                self.close()


def read_fbx_metadata(data: bytes, stem: str) -> tuple[str, str, str]:
    fc, fv = fbx_normalize.fbx_content_fingerprints(data, stem)
    try:
        roots = fbx_root.read_fbx_root_names_from_bytes(data)
    except (OSError, ValueError, struct.error):
        roots = []
    return fc, fv, roots[0] if roots else ''
