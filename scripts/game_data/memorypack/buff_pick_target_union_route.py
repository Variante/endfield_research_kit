"""Current PickTarget union new-child control and closed shared packable return."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts, validate_typed_usage_context
from scripts.game_data.memorypack import buff_action_reference as references
from scripts.game_data.memorypack.buff_timeline_read_value import SCHEMA as READ_VALUE_SCHEMA
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.packable_reference_sources import validate_packable_context, validate_packable_transfer
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
from scripts.game_data.memorypack.union_route_sources import (
    validate_indexed_union_prefix, validate_null_cast_return,
    validate_new_child_union_route, validate_packable_thunk)

LABEL = 'buffPickTargetUnionRoute'
SCHEMA = 'endfield.buff-pick-target-union-route-native-contract.v1'
SCOPE = 'selected-indexed-pick-target-new-child-and-packable-return-only'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_pick_target_union_route_native.json'


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
                           expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, scope=SCOPE)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract() -> dict:
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (c.get('scope') != SCOPE or set(c['dependencies']) != {
            'actionReference', 'header', 'source', 'rootPackable', 'readValue', 'instance'}):
        _fail('route-scope', 'one current child with six exact native dependencies', c.get('scope'))
    return c


def _validate_image(image: Any, c: dict) -> dict:
    schemas = {'actionReference': references.SCHEMA,
        'header': 'endfield.buff-action-union-header-native-contract.v1',
        'source': 'endfield.skill-timeline-pick-target-native-contract.v1',
        'rootPackable': 'endfield.buff-timeline-root-list-native-contract.v1',
        'readValue': READ_VALUE_SCHEMA,
        'instance': 'endfield.buff-timeline-instance-native-contract.v1'}
    deps = {k: read_reviewed_contract(CONTRACTS_DIR / c['dependencies'][k], schema=s,
            status='exact-current-build', label=LABEL)[0] for k, s in schemas.items()}
    if any(d['nativeInputs'] != c['nativeInputs'] for d in deps.values()):
        _fail('route-dependency-build', c['nativeInputs'], {k: d['nativeInputs'] for k, d in deps.items()})
    action, header, source, packable, value, instance = (deps[k] for k in schemas)
    action_summary = references._validate_image(image, action)
    image.validate_dispatcher(source['dispatcher'], label=LABEL)
    if (c['indexedPrefix']['codeWindows'] != header['callerPrefix']['codeWindows']
            or c['indexedPrefix']['program'][:17] != header['callerPrefix']['program']):
        _fail('current-indexed-caller', 'same current initialized caller prefix and owned window', c['indexedPrefix'])
    prefix = validate_indexed_union_prefix(image, c['indexedPrefix'], source['dispatcher'],
                                           header['helperEntryRva'], fail=_fail)
    route, cast, child, thunk = (c[k] for k in ('routeProgram', 'castUsage', 'childUsage', 'thunkUsage'))
    wrapper = source['dispatcher']['wrapperName']
    for usage in (cast, child, thunk):
        validate_typed_usage_context(image, usage, label=LABEL)
    if (cast['tag'] != 1 or cast['typeName'] != wrapper
            or child['tag'] != 6 or child['typeName'] != 'MemoryPack.MemoryPackReader'
            or child['methodName'] != 'ReadPackable' or child['classArguments'] != []
            or child['methodArguments'] != [wrapper] or thunk['methodSpec'] != child['methodSpec']
            or thunk['methodSpecIndex'] != child['methodSpecIndex']
            or thunk['methodArguments'] != child['methodArguments']):
        _fail('route-child-type-context', 'same selected concrete wrapper and closed Reader.ReadPackable context', child)
    if (route['program'][0][0] != source['dispatcher']['switchTargetRva']
            or route['codeWindows'][0] != source['dispatcher']['routeWindow']
            or route['codeWindows'][1:] != header['callerPrefix']['codeWindows']):
        _fail('route-and-return-owner', 'actual selected route and same complete caller return window', route)
    calls = c['calls']
    if (set(calls) != {'cast', 'child', 'barrier'}
            or calls['cast'] != c['nullCastProgram']['program'][0][0]
            or calls['child'] != c['childThunk']['program'][0][0]
            or calls['barrier'] != action['barrierTrampoline']['program'][0][0]):
        _fail('route-actual-helper-entries', 'same cast, closed thunk and actual shared barrier jump entries', calls)
    null_cast = validate_null_cast_return(image, c['nullCastProgram'], fail=_fail)
    selected_route = validate_new_child_union_route(image, route, cast, child, calls, fail=_fail)
    provider = next(r for r in instance['methodContexts'] if r['typeName'] == 'MemoryPack.MemoryPackFormatterProvider')
    contexts = [value['readValueContext'], provider, packable['packableContext']]
    validate_generic_contexts(image, contexts, label=LABEL)
    entries = GenericEntries(image)
    read_context = validate_read_value_context(image, contexts[0], provider, entries, fail=_fail)
    owned = validate_packable_context(image, contexts[2], read_context['readerMethodDefinition'], entries, fail=_fail)
    if child['methodSpec'][:2] != [owned['packableDefinition'], -1]:
        _fail('child-declared-packable-owner', owned['packableDefinition'], child['methodSpec'])
    expected_calls = {k: value['calls'][k] for k in packable['packableCalls']}
    if packable['packableCalls'] != expected_calls:
        _fail('child-packable-physical-dependencies', expected_calls, packable['packableCalls'])
    transfer = validate_packable_transfer(image, packable['packableProgram'], packable['packableCalls'], fail=_fail)
    closed = validate_packable_thunk(image, c['childThunk'], thunk,
                                     packable['packableProgram']['program'][0][0], fail=_fail)
    return {'selectedIndexedUnionPrefix': prefix, 'nullCastReturn': null_cast,
            'completeNewChildRoute': selected_route, 'closedPackableThunk': closed,
            'ownedReadValueContext': read_context, 'ownedPackableContext': owned,
            'completeSharedPackableTransfer': transfer,
            'unionBarrierMatchesSharedFalsePath': True,
            'barrierDisabledCondition': action_summary['unionFalseReturn']['condition'],
            'actualArrayCallbackSelection': 'unresolved',
            'concreteChildSourceAndCursorComposition': 'unresolved',
            'runtimeProviderSelectionObserved': False}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None) -> dict:
    c = _contract()
    pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'scope': SCOPE, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing', 'detail': 'UnityPlayer.dll missing or mismatched',
                'scope': SCOPE, 'nativeInputs': pins}
    try:
        summary = _validate_image(open_native_image(gate.gameassembly, gate.metadata), c)
    except ValueError as error:
        if isinstance(error, CensusGateError):
            raise
        _fail('native-pick-target-route', 'current indexed route, typed child context and full output/return joins', str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                         gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
                'detail': 'native inputs changed during PickTarget route validation', 'scope': SCOPE, 'nativeInputs': pins}
    return {'status': 'validated', 'scope': SCOPE, 'nativeInputs': pins, 'summary': summary,
            'childSchemaAdmitted': False, 'positiveListAdmitted': False, 'wholeRootAdmitted': False,
            'runtimeMeaningExact': False, 'reservedMarkerCanonicalAdmission': False, 'evidenceBoundary': c['evidenceBoundary']}
