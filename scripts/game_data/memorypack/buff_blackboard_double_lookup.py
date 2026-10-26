"""Current BlackboardDouble keyed Try composed with the managed lookup relation.

Both existing native owners authenticate their complete conditional programs.
This owner closes their call boundary without adding a duplicate native catalog.
"""
from __future__ import annotations
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.memorypack import buff_blackboard_double_consumers as consumer_owner
from scripts.game_data.memorypack import buff_blackboard_number_lookup as lookup_owner
from scripts.game_data.memorypack import closed_scalar_lookup as control
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _package_import_closure

LABEL = 'buffBlackboardDoubleLookup'


def _fail(check, expected, actual):
    error = CensusGateError(LABEL + '.' + check, source=consumer_owner.CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, record='Beyond.Blackboard+BlackboardDouble.TryGetValueInternal')
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _skip(status, detail, pins):
    return {'status': status, 'detail': detail, 'nativeInputs': pins,
            'wholeActionAdmitted': False, 'wholeRootAdmitted': False}


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict:
    paths = set(_package_import_closure(Path(__file__))) | {consumer_owner.CONTRACT_PATH,
        lookup_owner.CONTRACT_PATH, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH}
    inputs = {r['path']: r for r in (_fingerprint(p) for p in paths)}
    caller = consumer_owner._contract(); callee = lookup_owner._contract(); pins = caller['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return _skip(gate.status, gate.detail, pins)
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    if not unity.is_file():
        return _skip('missing', 'UnityPlayer.dll missing beside selected native image', pins)
    if _fingerprint(unity)['sha256'] != pins['UnityPlayer.dll']:
        return _skip('mismatched', 'Selected UnityPlayer.dll hash differs', pins)
    if callee['nativeInputs'] != pins or caller['numberLookupMethod'] != callee['method']:
        return _skip('mismatched', 'Caller and lookup declarations disagree on build or actual method', pins)
    results = {}
    for role, owner in [('consumer', consumer_owner), ('lookup', lookup_owner)]:
        result = owner.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata)
        if result['status'] != 'validated':
            return _skip(result['status'], role + ' dependency not current: ' + result.get('detail', ''), pins)
        if result['nativeInputs'] != pins:
            return _skip('mismatched', role + ' dependency belongs to another selected build', pins)
        for before in result['provenance']['inputs']:
            current = _fingerprint(Path(before['path']))
            if current != before or inputs.setdefault(before['path'], before) != before:
                _fail('dependency-source-drift', before, current)
        results[role] = result
    relation = control.compose(caller, callee, results['consumer']['consumerTransfer'],
        results['lookup']['selectedManagedLookup'], fail=_fail)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        return _skip(after.status, after.detail, pins)
    if not unity.is_file() or _fingerprint(unity)['sha256'] != pins['UnityPlayer.dll']:
        return _skip('missing' if not unity.is_file() else 'mismatched', 'Selected UnityPlayer.dll changed during validation', pins)
    for before in inputs.values():
        current = _fingerprint(Path(before['path']))
        if current != before:
            _fail('source-drift', before, current)
    return {'status': 'validated', 'nativeInputs': pins, 'selectedKeyedLookupRelation': relation,
        'dependencyProofs': {role: {'consumerTransfer' if role == 'consumer' else 'selectedManagedLookup': result[
            'consumerTransfer' if role == 'consumer' else 'selectedManagedLookup']} for role, result in results.items()},
        'provenance': {'inputs': sorted(inputs.values(), key=lambda r: r['path'])},
        'selectedKeyedConsumerAndManagedLookupComposed': True, 'evidenceBoundary': 'conditional',
        'actualLookupFoundValueProved': False, 'runtimeExecutionKnown': False,
        'dataInstanceToConsumerInstanceCorrespondenceProved': False, 'publicGetValueEndToEndProved': False,
        'providerSelectionProved': False, 'allDispatchAndFailureEffectsProved': False,
        'wholeActionAdmitted': False, 'wholeRootAdmitted': False}
