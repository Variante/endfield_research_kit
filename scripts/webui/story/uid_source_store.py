"""Reuse one verified current LevelScript UID decode across builders.

Decoding the selected LevelScript corpus through the current native owner is
the most expensive step Story and Map share, and before this store each
consumer (three Story passes, every Map worker) repeated it in full. A fully
verified batch now leaves its per-file ``(records, action-map membership)``
here, and a later call may project those rows instead of decoding again.

What a reuse proves, and what it does not:

* The store key binds the reader inputs a decode can depend on: every
  non-Python reader input (all contracts and external helpers), the roster
  of reader Python files, and the bytes of each reader module the deciding
  process had loaded when its rows were committed (``sys.modules`` sees
  static and ``import_module`` imports alike, so it is a superset of the
  code the decode ran). An edit to a reader module the decode never loaded
  therefore keeps the rows; any edit to loaded code, any contract edit, or
  an added/removed module misses. Reuse still runs under the complete
  reader snapshot's entry/exit bookends. The key also binds the selected
  ``GameAssembly.dll``/``global-metadata.dat``/``UnityPlayer.dll`` bytes, the
  exported StringPool pages, the code that framed the rows, and the
  interpreter. Each row is also bound to its own source bytes.
* Before a row is reused the selected source inventory is authenticated again
  against the installed client and the export, and must return the receipt the
  decode saw; that receipt pins every exported JsonData file, so a changed
  LevelData or Interactive table is a miss too. Every key input, the inventory
  files and every selected source file are measured again after projection;
  drift raises instead of returning.
* A row is written only after the fresh batch passed all of its native,
  source, reader and physical-EOF exit checks. Nothing native is stored: no
  proof, capability or validator result, only decoded rows.
* Any unreadable, incomplete or mismatched store is a miss and falls back to
  the fresh decode. The store is an optional run intermediate under
  ``webui/data/_build/work/``; deleting it is always safe, and a clean checkout
  builds without it. ``ENDFIELD_LEVELSCRIPT_UID_STORE=0`` disables it.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import shutil
import sys
import time
from pathlib import Path

from scripts.common import WEBUI_BUILD_DIR

SCHEMA = 'endfield.story-uid-source-store.v2'
STORE_ROOT = WEBUI_BUILD_DIR / 'work' / 'levelscript_uid_sources'
DISABLE_ENV = 'ENDFIELD_LEVELSCRIPT_UID_STORE'
PICKLE_PROTOCOL = 4
_STALE_STAGING_SECONDS = 24 * 3600
_CODE_PATHS = (Path(__file__).resolve(), Path(__file__).resolve().with_name('uid_batch.py'))


def enabled() -> bool:
    return os.environ.get(DISABLE_ENV, '').strip().lower() not in ('0', 'false', 'off', 'no')


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _file_sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def canonical_digest(value) -> str:
    """Digest of a JSON-shaped measurement, independent of key order."""
    return _sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                              separators=(',', ':'), default=str).encode('utf-8'))


def loaded_reader_code(batch_inputs) -> list:
    """Reader Python files this process has imported, as recorded snapshot paths."""
    rows = {row['path'] for row in batch_inputs['reader']['files'] if row['path'].endswith('.py')}
    loaded = set()
    for module in list(sys.modules.values()):
        origin = getattr(module, '__file__', None)
        if origin:
            path = Path(origin).resolve().as_posix()
            if path in rows:
                loaded.add(path)
    return sorted(loaded)


def reader_key(reader_snapshot, code_paths) -> str:
    """Digest of the reader inputs a decode that loaded ``code_paths`` can depend on."""
    code = set(code_paths)
    files = reader_snapshot['files']
    return canonical_digest(dict(
        schema=reader_snapshot.get('schema'),
        roster=sorted(row['path'] for row in files if row['path'].endswith('.py')),
        data=[row for row in files if not row['path'].endswith('.py')],
        code=[row for row in files if row['path'] in code],
        missingCode=sorted(code - {row['path'] for row in files}),
    ))


def key_inputs(*, family, pool_root, game_root, batch_inputs, code_paths) -> dict:
    """Every cheap-to-measure decode input, as digests; equal inputs give an equal key.

    ``batch_inputs`` is the reader/native/StringPool measurement the guarded
    batch uses as its own entry and exit bookends; ``code_paths`` names the
    reader modules the deciding decode had loaded (see ``reader_key``). The
    source inventory is not part of the key: its authenticated receipt is
    recorded beside the rows and must be reproduced by a fresh authentication
    before any reuse.
    """
    return dict(
        schema=SCHEMA,
        python=list(sys.version_info[:3]),
        pickleProtocol=PICKLE_PROTOCOL,
        family=family,
        jsonRoot=Path(pool_root).as_posix(),
        gameRoot=Path(game_root).as_posix(),
        storeCode={path.name: _file_sha256(path) for path in _CODE_PATHS},
        readerInputs=reader_key(batch_inputs['reader'], code_paths),
        nativeInputs=dict(batch_inputs['native']),
        stringPool=canonical_digest(batch_inputs['pool']),
    )


def source_files(summary_path, ledger_path) -> dict:
    """Bytes of the selected source-inventory files, for cheap drift checks."""
    return dict(summary=_file_sha256(Path(summary_path)), ledger=_file_sha256(Path(ledger_path)))


def _shard_name(family_root: Path, path: Path) -> str:
    relative = path.parent.relative_to(family_root).as_posix()
    return '.' if relative in ('', '.') else relative


class UidSourceStore:
    """One family's rows under one export root. Readers never trust it blindly."""

    def __init__(self, pool_root: Path, family: str, *, store_root: Path | None = None):
        self.pool_root = Path(pool_root)
        self.family = family
        self.family_root = self.pool_root / family
        export_tag = hashlib.sha256(self.pool_root.as_posix().lower().encode('utf-8')).hexdigest()[:16]
        self.directory = Path(store_root or STORE_ROOT) / export_tag / family
        self.manifest_path = self.directory / 'manifest.json'

    # -- reading ---------------------------------------------------------

    def _manifest(self):
        try:
            value = json.loads(self.manifest_path.read_bytes())
        except (OSError, ValueError):
            return None
        if (not isinstance(value, dict) or value.get('schema') != SCHEMA
                or not isinstance(value.get('files'), dict)
                or not isinstance(value.get('shards'), dict)
                or not isinstance(value.get('keyInputs'), dict)
                or not isinstance(value.get('readerCode'), list)
                or not isinstance(value.get('sourceReceipt'), str)):
            return None
        return value

    def recorded_code(self):
        """Reader module paths the stored rows' decode had loaded, or ``None``."""
        manifest = self._manifest()
        return None if manifest is None else list(manifest['readerCode'])

    def lookup(self, key: dict, signatures: dict):
        """Return a reader for ``signatures`` (path -> length/sha256) or a miss reason."""
        manifest = self._manifest()
        if manifest is None:
            return None, 'no usable store'
        if manifest['keyInputs'] != key:
            changed = sorted(name for name in set(key) | set(manifest['keyInputs'])
                             if key.get(name) != manifest['keyInputs'].get(name))
            return None, f'inputs changed: {", ".join(changed)}'
        for path, signature in signatures.items():
            try:
                row = manifest['files'].get(path.relative_to(self.family_root).as_posix())
            except ValueError:
                return None, f'outside the family root: {path}'
            if row is None:
                return None, f'not stored: {path.name}'
            if row.get('length') != signature['length'] or row.get('sha256') != signature['sha256']:
                return None, f'source bytes changed: {path.name}'
        return _Reader(self, manifest), None

    # -- writing ---------------------------------------------------------

    def writer(self):
        return _Writer(self)


class _Reader:
    def __init__(self, store: UidSourceStore, manifest: dict):
        self.store = store
        self.manifest = manifest
        self.source_receipt = manifest['sourceReceipt']
        self._shard_name = None
        self._shard = None

    def _load_shard(self, name: str) -> dict:
        row = self.manifest['shards'].get(name)
        if not isinstance(row, dict):
            raise LookupError(f'shard not recorded: {name}')
        raw = (self.store.directory / row['file']).read_bytes()
        if len(raw) != row['length'] or _sha256(raw) != row['sha256']:
            raise LookupError(f'shard bytes differ from the manifest: {name}')
        value = pickle.loads(raw)
        if not isinstance(value, dict):
            raise LookupError(f'shard shape: {name}')
        return value

    def payload(self, path: Path, signature: dict) -> bytes:
        """The pickled ``(records, membership)`` of one source; raises on any gap."""
        name = _shard_name(self.store.family_root, path)
        if name != self._shard_name:
            self._shard = self._load_shard(name)
            self._shard_name = name
        row = self._shard.get(path.name)
        if (not isinstance(row, tuple) or len(row) != 3 or row[0] != signature['length']
                or row[1] != signature['sha256'] or not isinstance(row[2], bytes)):
            raise LookupError(f'row missing or bound to other source bytes: {path.name}')
        return row[2]

    def verify(self, paths) -> None:
        """Read every needed shard once, so a damaged store is a miss before any projection."""
        for name in sorted({_shard_name(self.store.family_root, path) for path in paths}):
            self._load_shard(name)


class _Writer:
    """Stage rows per source folder; publish only when the caller commits."""

    def __init__(self, store: UidSourceStore):
        self.store = store
        self.staging = store.directory / f'.staging-{os.getpid()}-{time.monotonic_ns()}'
        self.files = {}
        self.shards = {}
        self._name = None
        self._rows = {}
        self.failed = None

    def add(self, path: Path, signature: dict, records, membership) -> None:
        """Stage one decoded row as it left the decoder, before any projection."""
        if self.failed:
            return
        try:
            payload = pickle.dumps((records, membership), protocol=PICKLE_PROTOCOL)
            if pickle.loads(payload) != (records, membership):
                raise ValueError(f'row does not survive a round trip: {path.name}')
            name = _shard_name(self.store.family_root, path)
            if name != self._name:
                self._flush()
                self._name = name
                if name in self.shards:
                    raise ValueError(f'source folder revisited: {name}')
            self._rows[path.name] = (signature['length'], signature['sha256'], payload)
            self.files[path.relative_to(self.store.family_root).as_posix()] = dict(
                length=signature['length'], sha256=signature['sha256'], shard=name)
        except Exception as error:  # a row that cannot be stored only disables the store
            self.failed = f'{type(error).__name__}: {str(error)[:300]}'

    def _flush(self) -> None:
        if self._name is None:
            return
        raw = pickle.dumps(self._rows, protocol=PICKLE_PROTOCOL)
        digest = _sha256(raw)
        stem = hashlib.sha256(self._name.encode('utf-8')).hexdigest()[:16]
        file_name = f'{stem}.{digest[:16].lower()}.bin'
        self.staging.mkdir(parents=True, exist_ok=True)
        (self.staging / file_name).write_bytes(raw)
        self.shards[self._name] = dict(file=file_name, length=len(raw), sha256=digest)
        self._name, self._rows = None, {}

    def discard(self) -> None:
        shutil.rmtree(self.staging, ignore_errors=True)

    def commit(self, key: dict, source_receipt: str, code_paths) -> str | None:
        """Publish the staged rows. Returns a reason when nothing was published."""
        if self.failed:
            self.discard()
            return self.failed
        try:
            self._flush()
            if not self.files:
                self.discard()
                return 'no rows'
            store = self.store
            files, shards = dict(self.files), dict(self.shards)
            previous = store._manifest()
            if (previous is not None and previous['keyInputs'] == key
                    and previous['sourceReceipt'] == source_receipt
                    and previous['readerCode'] == list(code_paths)):
                # Same inputs: keep rows of source folders this batch did not decode.
                for name, row in previous['shards'].items():
                    shards.setdefault(name, row)
                for name, row in previous['files'].items():
                    if row.get('shard') not in self.shards:
                        files.setdefault(name, row)
            store.directory.mkdir(parents=True, exist_ok=True)
            for row in self.shards.values():
                os.replace(self.staging / row['file'], store.directory / row['file'])
            manifest = dict(schema=SCHEMA, keyInputs=key, sourceReceipt=source_receipt,
                            readerCode=list(code_paths), files=files, shards=shards)
            pending = store.directory / f'manifest.{os.getpid()}.tmp'
            pending.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True),
                               encoding='utf-8', newline='\n')
            os.replace(pending, store.manifest_path)
            self._prune({row['file'] for row in shards.values()})
            return None
        except (OSError, ValueError, pickle.PicklingError) as error:
            return f'{type(error).__name__}: {error}'
        finally:
            self.discard()

    def _prune(self, keep: set) -> None:
        """Drop rows no manifest names, and staging folders an aborted run left."""
        now = time.time()
        for path in self.store.directory.iterdir():
            try:
                if path.is_file() and path.suffix == '.bin' and path.name not in keep:
                    path.unlink()
                elif (path.is_dir() and path.name.startswith('.staging-') and path != self.staging
                        and now - path.stat().st_mtime > _STALE_STAGING_SECONDS):
                    shutil.rmtree(path, ignore_errors=True)
            except OSError:
                continue
