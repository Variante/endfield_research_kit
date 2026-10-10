"""Shared gate shape for native-owner wrappers over one reviewed contract.

A wrapper module names its contract, label and scope, and supplies
``_contract``, ``_proof_sources``, ``_validate_selected``, ``_fail`` and the
module-level ``check_installed_native_inputs``/``_fingerprint`` references.
``validate_owner`` runs the common fail-closed sequence against those
references, looked up on the wrapper at call time so a test patching the
wrapper's own gate still decides the result:

1. gate ``GameAssembly.dll``/``global-metadata.dat`` against ``nativeInputs``;
2. check ``UnityPlayer.dll`` beside the selected GameAssembly;
3. run the wrapper's selected-body proof, converting a decoder error into the
   wrapper's own named failure;
4. re-gate all three inputs afterwards, so a build change during the proof
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


def _unity_hash(unity):
    if not unity.is_file():
        return None
    with unity.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def validate_owner(owner, *, gameassembly, metadata, open_claims, check, expected, phase,
                   pass_native_inputs=True):
    """Run the shared gate sequence for wrapper module ``owner`` (see module docstring).

    ``open_claims`` are the result flags the wrapper never proves; ``check`` and
    ``expected`` name the failure raised when the selected proof errors; ``phase``
    names the validation in the native-drift detail. ``pass_native_inputs``
    forwards the pinned inputs to the wrapper's ``_fail`` diagnostics.
    """
    c = owner._contract(); pins = c['nativeInputs']; sources = owner._proof_sources()
    extra = {'native_inputs': pins} if pass_native_inputs else {}
    gate = owner.check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                               gameassembly=gameassembly, metadata=metadata)
    result = {'status': gate.status, 'scope': owner.SCOPE, 'nativeInputs': pins,
              'provenance': {'inputs': sources}, 'evidenceBoundary': c['evidenceBoundary'], **open_claims}
    if gate.status != 'validated':
        return {**result, 'detail': gate.detail}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    current = _unity_hash(unity)
    if current != pins['UnityPlayer.dll']:
        return {**result, 'status': 'missing' if current is None else 'mismatched',
                'detail': 'UnityPlayer.dll missing or mismatched'}
    try:
        summary = owner._validate_selected(gate.gameassembly, c)
    except (ValueError, KeyError, IndexError, TypeError, OverflowError) as error:
        if isinstance(error, CensusGateError):
            raise
        owner._fail(check, expected, str(error), **extra)
    after = owner.check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                                gameassembly=gate.gameassembly, metadata=gate.metadata)
    current = _unity_hash(unity)
    if after.status != 'validated' or current != pins['UnityPlayer.dll']:
        return {**result, 'status': after.status if after.status != 'validated' else (
                'missing' if current is None else 'mismatched'),
                'detail': f'native inputs changed during {phase} validation'}
    drift = [r['path'] for r in sources if owner._fingerprint(Path(r['path'])) != r]
    if drift:
        owner._fail('proof-source-drift', 'unchanged source/contract closure', drift, **extra)
    return {**result, 'status': 'validated', 'summary': summary}
