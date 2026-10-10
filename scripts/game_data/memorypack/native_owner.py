"""Shared gate shape for native-owner wrappers over one reviewed contract.

A wrapper module names its contract, label and scope, and supplies
``_contract``, ``_proof_sources``, ``_validate_selected``, ``_fail`` and the
module-level ``check_installed_native_inputs``/``_fingerprint`` references.
``validate_owner`` runs the common fail-closed sequence against those
references, looked up on the wrapper at call time so a test patching the
wrapper's own gate still decides the result:

1. gate ``GameAssembly.dll``/``global-metadata.dat`` against ``nativeInputs``;
2. check ``UnityPlayer.dll`` beside the selected GameAssembly;
3. check any explicitly selected additional native libraries, then run the
   wrapper's selected-body proof, converting a decoder error into the
   wrapper's own named failure;
4. re-gate every selected native input afterwards, so a build change during the proof
   discards its summary;
5. refuse when any proof source or contract changed during the run.

A missing or mismatched input yields the open-claim result with no summary.
This module proves nothing about any body; the wrapper's proof does.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _parser_source_snapshots


def fail(label, scope, path, check, expected, actual, *, native_inputs=None):
    """Raise the wrapper's CensusGateError naming ``label.check`` and its source contract."""
    error = CensusGateError(f'{label}.{check}', source=path.as_posix(),
                            expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=label, scope=scope)
    if native_inputs is not None:
        error.diagnostic['expectedNativeInputs'] = native_inputs
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def proof_sources(entry, path, parent_sources, mapper_path):
    """Fingerprint the wrapper's import closure, its contract, the mapper and its parent's closure."""
    rows = _parser_source_snapshots(Path(entry)) + [_fingerprint(path), _fingerprint(mapper_path)] + parent_sources
    return sorted({r['path']: r for r in rows}.values(), key=lambda r: r['path'])


def _file_hash(path):
    if not path.is_file():
        return None
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def validate_owner(owner, *, gameassembly, metadata, open_claims, check, expected, phase,
                   pass_native_inputs=True, additional_inputs=None):
    """Run the shared gate sequence for wrapper module ``owner`` (see module docstring).

    ``open_claims`` are the result flags the wrapper never proves; ``check`` and
    ``expected`` name the failure raised when the selected proof errors; ``phase``
    names the validation in the native-drift detail. ``pass_native_inputs``
    forwards the pinned inputs to the wrapper's ``_fail`` diagnostics.
    ``additional_inputs`` maps a declared library name to an explicit path, or
    None to select that file beside the explicitly gated GameAssembly. Every
    contract native input must be selected; an extra pin is never silently ignored.
    With additional inputs, the selected-body proof receives ``selected_inputs``
    containing their actual paths so an explicit selection cannot be discarded.
    """
    c = owner._contract(); pins = c['nativeInputs']; sources = owner._proof_sources()
    extra = {'native_inputs': pins} if pass_native_inputs else {}
    additional_inputs = {} if additional_inputs is None else dict(additional_inputs)
    standard = {'GameAssembly.dll', 'global-metadata.dat', 'UnityPlayer.dll'}
    if (set(additional_inputs) & standard or set(pins) != standard | set(additional_inputs) or
        any(type(name) != str or not name or '/' in name or '\\' in name or
            name in ('.', '..') for name in additional_inputs)):
        owner._fail('native-input-selection', 'every declared native input selected exactly once',
                    sorted(pins), **extra)
    gate = owner.check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                               gameassembly=gameassembly, metadata=metadata)
    result = {'status': gate.status, 'scope': owner.SCOPE, 'nativeInputs': pins,
              'provenance': {'inputs': sources}, 'evidenceBoundary': c['evidenceBoundary'], **open_claims}
    if gate.status != 'validated':
        return {**result, 'detail': gate.detail}
    selected = {'UnityPlayer.dll': Path(gate.gameassembly).parent / 'UnityPlayer.dll'}
    selected.update({name: Path(path) if path is not None else Path(gate.gameassembly).parent / name
                     for name, path in sorted(additional_inputs.items())})
    current = {name: _file_hash(path) for name, path in selected.items()}
    for name, digest in current.items():
        if digest != pins[name]:
            return {**result, 'status': 'missing' if digest is None else 'mismatched',
                    'detail': f'{name} missing or mismatched'}
    try:
        summary = (owner._validate_selected(gate.gameassembly, c, selected_inputs=selected)
                   if additional_inputs else owner._validate_selected(gate.gameassembly, c))
    except (ValueError, KeyError, IndexError, TypeError, OverflowError) as error:
        if isinstance(error, CensusGateError):
            raise
        owner._fail(check, expected, str(error), **extra)
    after = owner.check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                                gameassembly=gate.gameassembly, metadata=gate.metadata)
    current = {name: _file_hash(path) for name, path in selected.items()}
    changed = [name for name, digest in current.items() if digest != pins[name]]
    if after.status != 'validated' or changed:
        return {**result, 'status': after.status if after.status != 'validated' else (
                'missing' if current[changed[0]] is None else 'mismatched'),
                'detail': f'native inputs changed during {phase} validation'}
    drift = [r['path'] for r in sources if owner._fingerprint(Path(r['path'])) != r]
    if drift:
        owner._fail('proof-source-drift', 'unchanged source/contract closure', drift, **extra)
    return {**result, 'status': 'validated', 'summary': summary}
