"""Own Story's source-backed UID reads until all batch exit proofs pass.

The installed-format reader remains in game_data. These operations select
current source files and the explicit native build; they grant no owner EOF
or corpus authority, and keep no native proof across calls.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path

from scripts.common import resolve_installed_native_inputs
from scripts.game_data.codecs.levelscript.uid_records import (
    extract_levelscript_uid_records as _extract,
    levelscript_uid_records_require_native,
    project_current_framed_uid_records,
)
from scripts.game_data.levelscript_binary import levelscript_action_map_membership
from scripts.game_data.memorypack.levelscript_decode_batch import (
    LevelScriptDecodeBatchError, decode_levelscript_batch,
)


@dataclass(frozen=True)
class UidSource:
    data: bytes
    records: list
    membership: dict
    failure: dict | None = None


def _json_root(path):
    roots = [parent for parent in path.parents if parent.name == 'Json']
    if len(roots) != 1:
        raise LevelScriptDecodeBatchError('source-json-root', path,
            'one selected Json ancestor', len(roots))
    return roots[0]


def _source_note(error, path, raw):
    error.add_note(f'Story UID source: {path}; sha256={hashlib.sha256(raw).hexdigest().upper()}')


def _read(path):
    try:
        return path.read_bytes()
    except OSError as error:
        raise LevelScriptDecodeBatchError('selected-source-read', path,
            'readable current source', str(error)[:1000]) from error


def _signature(raw):
    return dict(length=len(raw), sha256=hashlib.sha256(raw).hexdigest().upper())


def load_uid_sources(paths, *, game_root=None, expected_data=None, progress=None,
                     preserve_failures=False, project=None, _current_sources=False):
    """Decode selected files together, returning nothing before exit checks.

    A family's common directory is the proof roster; unrelated files in it
    are hashed but not decoded or claimed as decoded. Separate families and
    Json roots never share a scope. The pool always comes from that selected
    source root. Empty/null action maps need neither a native installation
    nor a string-pool proof, since they contain no child records. An audit
    may explicitly preserve bounded per-file refusals; such a row has no
    decoded records and never grants successful child or owner coverage.
    ``project(path, source)`` may derive page-local results inside the same
    scope. Its results remain private until every source/native exit check
    succeeds; projection errors are never reclassified as decoder refusals.
    """
    if _current_sources and preserve_failures:
        raise ValueError('current Story owners cannot preserve incomplete decodes as unavailable rows')
    selected_paths = sorted({Path(path).resolve() for path in paths})
    expected = {Path(path).resolve(): _signature(bytes(raw))
                for path, raw in (expected_data or {}).items()}
    groups = defaultdict(list)
    for path in selected_paths:
        root = _json_root(path)
        relative = path.relative_to(root)
        family = relative.parts[0] if len(relative.parts) > 1 else ''
        groups[root, family].append(path)
    result = {}
    for (pool_root, _family), wanted in sorted(groups.items()):
        entry = {}
        refused = set()
        owner = None
        needs_native = _current_sources
        for path in wanted:
            raw = _read(path)
            entry[path] = _signature(raw)
            if path in expected and expected[path] != entry[path]:
                raise LevelScriptDecodeBatchError('caller-source-bytes', path,
                    expected[path], entry[path])
            if not needs_native:
                try:
                    needs_native = levelscript_uid_records_require_native(raw)
                except ValueError as error:
                    _source_note(error, path, raw)
                    if not preserve_failures:
                        raise
                    # The guarded decoder records this refusal; the probe
                    # never grants a successful framing or native result.
                    needs_native = True
        # Retain fingerprints, not a second copy of all selected payloads.
        del raw

        def decode(path, raw, selected_strings, selected_root):
            path = path.resolve()
            if path not in entry:
                return None
            if entry[path] != _signature(raw):
                raise LevelScriptDecodeBatchError('selected-source-read-drift', path,
                    entry[path], _signature(raw))
            try:
                if owner is None:
                    records = _extract(raw, source_path=path, strings=selected_strings,
                        game_root=selected_root)
                else:
                    if _family == 'LevelScriptTemplateData':
                        owner.prepare_template()
                    frame = (owner.frame_template if _family == 'LevelScriptTemplateData'
                             else owner.frame)(path, raw)
                    records = project_current_framed_uid_records(raw, frame)
                _map, membership = levelscript_action_map_membership(raw, records)
            except ValueError as error:
                _source_note(error, path, raw)
                if preserve_failures:
                    failure = dict(detail=str(error)[:1000],
                        diagnostics=getattr(error, 'diagnostics', getattr(error, 'diagnostic', None)),
                        sourceSha256=hashlib.sha256(raw).hexdigest().upper())
                    source = UidSource(raw, [], {}, failure)
                    refused.add(path)
                else:
                    raise
            else:
                source = UidSource(raw, records, membership)
            if selected_root is None and source.records:
                raise LevelScriptDecodeBatchError('empty-source-child-records', pool_root,
                    'no child records without native proofs', 'unexpected decoded children')
            return path, source if project is None else project(path, source)

        if needs_native:
            selected_root = (Path(game_root) if game_root is not None else
                             resolve_installed_native_inputs()[1].parents[2])
            source_root = Path(os.path.commonpath([str(path.parent) for path in wanted]))
            if _current_sources:
                from scripts.game_data.memorypack.levelscript_current_source import CurrentLevelScriptSource
                export_root = pool_root.parent.parent
                if (pool_root != export_root / 'game/Json'
                        or _family not in ('LevelScriptData', 'LevelScriptTemplateData')):
                    raise LevelScriptDecodeBatchError('current-selected-source-layout', pool_root,
                        '<selected export>/game/Json/{LevelScriptData,LevelScriptTemplateData}', _family)
                evidence = export_root / 'meta/evidence/animestudio'
                owner = CurrentLevelScriptSource.from_source_inventory(pool_root,
                    gameassembly=selected_root.parent / 'GameAssembly.dll',
                    metadata=selected_root / 'il2cpp_data/Metadata/global-metadata.dat',
                    summary_path=evidence / 'jsondata_source_current.json',
                    ledger_path=evidence / 'jsondata_source_files_current.jsonl.gz')
                rows, audit = decode_levelscript_batch(source_root, decode,
                    game_root=selected_root, json_root=pool_root, progress=progress,
                    operation=owner)
                closed = (len(owner.template_closed) if _family == 'LevelScriptTemplateData'
                          else len(owner.closed))
                audit['nativeValidationReuse'] = owner.native_validation_reuse
                if closed != len(wanted):
                    raise LevelScriptDecodeBatchError('current-owner-physical-EOF', pool_root,
                        len(wanted), closed)
                if progress:
                    progress(f'current native owners at physical EOF: {closed}; source/native exit proofs passed')
            else:
                rows, audit = decode_levelscript_batch(source_root, decode,
                    game_root=selected_root, json_root=pool_root, progress=progress)
            accepted = dict(row for row in rows if row is not None)
            if progress:
                reuse = audit['nativeValidationReuse']
                progress(f'decoded {len(accepted)-len(refused)} selected UID sources, refusals={len(refused)}; '
                    f'native proof hits={reuse["hits"]}, misses={reuse["misses"]}; '
                    'entry/exit proofs passed')
        else:
            accepted = dict(decode(path, _read(path), {}, None) for path in entry)
            for path, before in entry.items():
                after = _signature(_read(path))
                if before != after:
                    raise LevelScriptDecodeBatchError('empty-source-read-drift', path,
                        before, after)
        if set(accepted) != set(wanted):
            raise LevelScriptDecodeBatchError('selected-source-roster', pool_root,
                dict(count=len(wanted), first=[str(path) for path in wanted[:4]]),
                dict(count=len(accepted), missing=[str(path) for path in sorted(set(wanted)-set(accepted))][:4],
                     extra=[str(path) for path in sorted(set(accepted)-set(wanted))][:4]))
        result.update(accepted)
    return result


def load_current_uid_sources(paths, *, game_root=None, expected_data=None,
                             progress=None, project=None):
    """Ordinary Story reads use the same fresh current owner as Data.

    The selected source inventory, complete root grammar and independent
    current node values are mandatory. Unknown routes and missing evidence
    abort the operation; they never become unavailable replacement rows.
    """
    return load_uid_sources(paths, game_root=game_root, expected_data=expected_data,
        progress=progress, project=project, _current_sources=True)


def extract_uid_records(data, *, source_path=None, strings=None, game_root=None, **parameters):
    """Source-backed single-file operations also share child proofs safely.

    Byte-only and explicitly prepared/pool-backed calls keep the format
    reader's original behavior and their caller's existing proof scope.
    Unprepared source-backed exports use the guarded operation.
    Bulk callers use load_uid_sources rather than opening one scope per file.
    """
    if source_path is None or strings is not None or any(value is not None for value in parameters.values()):
        return _extract(data, source_path=source_path, strings=strings,
            game_root=game_root, **parameters)
    path = Path(source_path).resolve()
    return load_current_uid_sources([path], game_root=game_root, expected_data={path: data})[path].records
