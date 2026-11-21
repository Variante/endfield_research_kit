"""Reuse one complete current-owner projection across Story builds.

The Story interactive narrative and NPC patrol radio passes and the Audio
LevelScript pass each open a fresh
current LevelScript owner operation, derive its native owner proof and frame
every selected source file, only to project a few hundred stored-configuration
rows. When nothing they read has changed, the rows are the same; this store
keeps the last complete result and replays it instead.

What a reuse proves, and what it does not:

* The key binds the reader inputs the way the UID source store does
  (``uid_source_store.reader_key``: every non-Python reader input, the reader
  module roster and each reader module the deciding process had loaded), the
  bytes of every other loaded ``scripts`` module (the page projection code),
  the selected ``GameAssembly.dll``/``global-metadata.dat``/``UnityPlayer.dll``
  bytes, the exported StringPool pages, the length and SHA256 of every
  selected source file, and each caller-named input (story keys, side tables).
* The selected source inventory is authenticated again against the installed
  client and the export and must return the receipt the stored build saw.
* Every key input is measured again after the stored result is loaded; drift
  raises instead of returning.
* Only a result whose audit reports a complete pass is stored. Nothing native
  is stored, only the projected rows and their audit as the builder returned
  them. The replayed audit keeps the stored build's counters.
* Any unreadable or mismatched store is a miss and the builder runs afresh.
  The store is an optional intermediate under ``webui/data/_build/work/``;
  deleting it is always safe. ``ENDFIELD_OWNER_PROJECTION_STORE=0`` disables it.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import sys
from pathlib import Path

from scripts.common import WEBUI_BUILD_DIR
from scripts.repo_paths import REPO_ROOT
from scripts.webui.story import uid_source_store

SCHEMA = 'endfield.story-owner-projection-store.v1'
STORE_ROOT = WEBUI_BUILD_DIR / 'work' / 'owner_projections'
DISABLE_ENV = 'ENDFIELD_OWNER_PROJECTION_STORE'
PICKLE_PROTOCOL = 4
_SCRIPTS_ROOT = (REPO_ROOT / 'scripts').resolve()


def enabled() -> bool:
    return os.environ.get(DISABLE_ENV, '').strip().lower() not in ('0', 'false', 'off', 'no')


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def digest(value) -> str:
    """Key digest of a caller input; a value JSON cannot order is digested by pickle.

    A pickle digest follows insertion order, so an equal value built in another
    order only costs a store miss, never a wrong replay.
    """
    try:
        return uid_source_store.canonical_digest(value)
    except (TypeError, ValueError):
        return 'pickle:' + _sha256(pickle.dumps(value, protocol=PICKLE_PROTOCOL))


def loaded_scripts_code() -> list:
    """Every ``scripts`` Python file this process has imported."""
    loaded = set()
    for module in list(sys.modules.values()):
        origin = getattr(module, '__file__', None)
        if not origin or not origin.endswith('.py'):
            continue
        path = Path(origin).resolve()
        if path.is_relative_to(_SCRIPTS_ROOT):
            loaded.add(path.as_posix())
    return sorted(loaded)


def _source_signatures(source_roots) -> dict:
    rows = {}
    for root in source_roots:
        root = Path(root)
        for path in sorted(root.rglob('*.json')) if root.is_dir() else ():
            raw = path.read_bytes()
            rows[path.resolve().as_posix()] = [len(raw), _sha256(raw)]
    return rows


class OwnerProjectionStore:
    def __init__(self, name: str, json_root: Path, *, store_root: Path | None = None):
        self.name = name
        self.json_root = Path(json_root).resolve()
        tag = hashlib.sha256(self.json_root.as_posix().lower().encode('utf-8')).hexdigest()[:16]
        self.directory = Path(store_root or STORE_ROOT) / tag / name
        self.manifest_path = self.directory / 'manifest.json'
        self.value_path = self.directory / 'value.bin'

    def _manifest(self):
        try:
            value = json.loads(self.manifest_path.read_bytes())
        except (OSError, ValueError):
            return None
        if (not isinstance(value, dict) or value.get('schema') != SCHEMA
                or not isinstance(value.get('key'), dict) or not isinstance(value.get('code'), list)
                or not isinstance(value.get('sourceReceipt'), str)
                or not isinstance(value.get('valueSha256'), str)):
            return None
        return value

    def key(self, *, game_root, code_paths, source_roots, extra) -> dict:
        from scripts.game_data.memorypack.levelscript_decode_batch import measure_batch_inputs
        inputs = measure_batch_inputs(game_root, self.json_root)
        reader_rows = {row['path'] for row in inputs['reader']['files']}
        other = {}
        for path in code_paths:
            if path in reader_rows:
                continue
            try:
                other[path] = _sha256(Path(path).read_bytes())
            except OSError:
                other[path] = None
        return dict(
            schema=SCHEMA,
            python=list(sys.version_info[:3]),
            pickleProtocol=PICKLE_PROTOCOL,
            name=self.name,
            jsonRoot=self.json_root.as_posix(),
            gameRoot=Path(game_root).resolve().as_posix(),
            readerInputs=uid_source_store.reader_key(inputs['reader'],
                [path for path in code_paths if path in reader_rows]),
            projectionCode=uid_source_store.canonical_digest(other),
            nativeInputs=dict(inputs['native']),
            stringPool=uid_source_store.canonical_digest(inputs['pool']),
            sources=uid_source_store.canonical_digest(_source_signatures(source_roots)),
            extra=uid_source_store.canonical_digest(extra),
        )

    def load(self, key: dict, receipt: str):
        """The stored ``value`` for ``key``/``receipt``, or ``(None, reason)``."""
        manifest = self._manifest()
        if manifest is None:
            return None, 'no usable store'
        if manifest['key'] != key:
            changed = sorted(name for name in set(key) | set(manifest['key'])
                             if key.get(name) != manifest['key'].get(name))
            return None, f'inputs changed: {", ".join(changed)}'
        if manifest['sourceReceipt'] != receipt:
            return None, 'source inventory receipt changed'
        try:
            raw = self.value_path.read_bytes()
            if _sha256(raw) != manifest['valueSha256']:
                return None, 'stored value differs from its manifest'
            return pickle.loads(raw), None
        except (OSError, EOFError, ValueError, pickle.UnpicklingError) as error:
            return None, f'unreadable ({str(error)[:200]})'

    def save(self, key: dict, receipt: str, code_paths, value) -> str | None:
        try:
            raw = pickle.dumps(value, protocol=PICKLE_PROTOCOL)
            if pickle.loads(raw) != value:
                return 'value does not survive a round trip'
            self.directory.mkdir(parents=True, exist_ok=True)
            pending = self.directory / f'value.{os.getpid()}.tmp'
            pending.write_bytes(raw)
            os.replace(pending, self.value_path)
            manifest = dict(schema=SCHEMA, key=key, sourceReceipt=receipt, code=list(code_paths),
                            valueSha256=_sha256(raw))
            pending = self.directory / f'manifest.{os.getpid()}.tmp'
            pending.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True),
                               encoding='utf-8', newline='\n')
            os.replace(pending, self.manifest_path)
            return None
        except (OSError, ValueError, pickle.PicklingError) as error:
            return f'{type(error).__name__}: {error}'


def reuse_or_build(name, *, json_root, gameassembly, metadata, summary_path, ledger_path,
                   source_roots, extra, build, complete, progress=None):
    """Return ``build()``'s value, or the stored value of an identical earlier build.

    ``complete(value)`` decides whether a fresh value may be stored. Errors
    raised before replay starts fall back to ``build()``; once a stored value
    is selected, exit drift raises ``ValueError``.
    """
    def note(text):
        if progress:
            progress(f'[projection-store:{name}] {text}')

    if not enabled() or gameassembly is None or metadata is None:
        return build()
    from scripts.game_data.memorypack.levelscript_current_source import CurrentLevelScriptSource
    store = OwnerProjectionStore(name, json_root)
    try:
        game_root = Path(metadata).resolve().parents[2]
        owner = CurrentLevelScriptSource.from_receipt(store.json_root, gameassembly=Path(gameassembly),
            metadata=Path(metadata), summary_path=Path(summary_path), ledger_path=Path(ledger_path))
        receipt = uid_source_store.canonical_digest(owner.authenticate_selected_source())
        manifest = store._manifest()
        key = None
        if manifest is not None:
            key = store.key(game_root=game_root, code_paths=manifest['code'],
                            source_roots=source_roots, extra=extra)
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        note(f'projection store unusable ({str(error)[:200]}); building afresh')
        return build()
    if key is not None:
        value, reason = store.load(key, receipt)
        if reason is None:
            after = store.key(game_root=game_root, code_paths=manifest['code'],
                              source_roots=source_roots, extra=extra)
            if after != key or uid_source_store.canonical_digest(
                    owner.authenticate_selected_source()) != receipt:
                raise ValueError(f'storyOwnerProjectionStore.{name}.reused-input-drift')
            note('reused the stored complete projection; reader, native, StringPool, '
                 'source files and source inventory re-authenticated')
            return value
        note(f'projection store miss: {reason}; building afresh')
    else:
        note('projection store miss: no usable store; building afresh')
    value = build()
    if not complete(value):
        return value
    try:
        code_paths = loaded_scripts_code()
        key = store.key(game_root=game_root, code_paths=code_paths,
                        source_roots=source_roots, extra=extra)
        if uid_source_store.canonical_digest(owner.authenticate_selected_source()) != receipt:
            note('projection store not updated: source inventory receipt changed during the build')
            return value
        skipped = store.save(key, receipt, code_paths, value)
    except (OSError, ValueError, KeyError, TypeError) as error:
        skipped = f'{type(error).__name__}: {str(error)[:200]}'
    note('projection store ' + ('updated' if skipped is None else f'not updated ({skipped})'))
    return value
