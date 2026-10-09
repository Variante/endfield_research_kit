"""Current Tick union new-child output, reusing shared reviewed union facts.

This control owner does not admit stored parents. Normal-call, initialized
context/provider, null prior output and disabled-barrier conditions remain
explicit; native callback cursor equality and runtime selection are separate.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts, validate_typed_usage_context
from scripts.game_data.memorypack import buff_action_reference as references
from scripts.game_data.memorypack import buff_tick_interval_sources as sources
from scripts.game_data.memorypack.buff_timeline_read_value import SCHEMA as READ_VALUE_SCHEMA
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.packable_reference_sources import validate_packable_context, validate_packable_transfer
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
from scripts.game_data.memorypack.union_route_sources import (
    validate_indexed_union_prefix, validate_null_cast_return,
    validate_new_child_union_route, validate_packable_thunk)

LABEL = 'buffTickIntervalUnionRoute'
SCHEMA = 'endfield.buff-tick-interval-union-route-native-contract.v1'
SCOPE = 'selected-indexed-tick-interval-new-child-and-packable-return-only'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_tick_interval_union_route_native.json'


def _fail(check, expected, actual):
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, scope=SCOPE)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract():
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (c.get('scope') != SCOPE or c.get('sharedRouteContract') != 'buff_pick_target_union_route_native.json'
            or c.get('sourceContract') != sources.candidate.CONTRACT_PATH.name
            or c.get('fieldFlowsContract') != sources.CONTRACT_PATH.name
            or len(c.get('caseProgram', [])) != 11):
        _fail('route-contract-shape', 'selected complete Tick case with shared reviewed union facts', c.get('scope'))
    return c


def _validate_image(image, c):
    shared, _ = read_reviewed_contract(CONTRACTS_DIR / c['sharedRouteContract'],
        schema='endfield.buff-pick-target-union-route-native-contract.v1', status='exact-current-build', label=LABEL)
    source = sources.candidate._contract(); fields = sources._contract()
    schemas = {'actionReference': references.SCHEMA,
        'header': 'endfield.buff-action-union-header-native-contract.v1',
        'rootPackable': 'endfield.buff-timeline-root-list-native-contract.v1',
        'readValue': READ_VALUE_SCHEMA, 'instance': 'endfield.buff-timeline-instance-native-contract.v1'}
    deps = {k: read_reviewed_contract(CONTRACTS_DIR / shared['dependencies'][k], schema=s,
        status='exact-current-build', label=LABEL)[0] for k, s in schemas.items()}
    if any(d['nativeInputs'] != c['nativeInputs'] for d in [shared, source, fields, *deps.values()]):
        _fail('route-dependency-build', c['nativeInputs'], [d.get('nativeInputs') for d in [shared, source, fields, *deps.values()]])
    if (c['sourceContract'] != sources.candidate.CONTRACT_PATH.name or c['fieldFlowsContract'] != sources.CONTRACT_PATH.name
            or source['dispatcher']['wrapperTypeDefinition'] != fields['wrapper']['typeDefinition']
            or source['dispatcher']['wrapperName'] != fields['wrapper']['wrapperName']
            or fields['wrapper']['wrappedType'] != 'Beyond.Gameplay.Core.TickIntervalAction+Data'):
        _fail('same-owned-tick-wrapper', fields['wrapper'], source['dispatcher'])
    action, header, packable, value, instance = (deps[k] for k in schemas)
    action_summary = references._validate_image(image, action)
    image.validate_dispatcher(source['dispatcher'], label=LABEL)
    prefix = shared['indexedPrefix']
    if (prefix['codeWindows'] != header['callerPrefix']['codeWindows']
            or prefix['program'][:17] != header['callerPrefix']['program']
            or len(shared['routeProgram']['program']) != 18):
        _fail('shared-owned-union-prefix-return', 'same complete indexed prefix and seven-instruction return', prefix)
    indexed = validate_indexed_union_prefix(image, prefix, source['dispatcher'], header['helperEntryRva'], fail=_fail)
    cast, child, thunk = (c[k] for k in ('castUsage', 'childUsage', 'thunkUsage'))
    wrapper = source['dispatcher']['wrapperName']
    for usage in (cast, child, thunk): validate_typed_usage_context(image, usage, label=LABEL)
    if (cast['tag'] != 1 or cast['typeName'] != wrapper or child['tag'] != 6
            or child['typeName'] != 'MemoryPack.MemoryPackReader' or child['methodName'] != 'ReadPackable'
            or child['classArguments'] != [] or child['methodArguments'] != [wrapper]
            or thunk['methodSpec'] != child['methodSpec'] or thunk['methodSpecIndex'] != child['methodSpecIndex']
            or thunk['methodArguments'] != child['methodArguments'] or thunk['tag'] != 6
            or thunk['typeName'] != child['typeName'] or thunk['methodName'] != child['methodName']
            or thunk['classArguments'] != child['classArguments']):
        _fail('same-current-closed-child-usage', wrapper, [cast, child, thunk])
    case = c['caseProgram']; window = source['dispatcher']['routeWindow']
    if (case[0][0] != source['dispatcher']['switchTargetRva'] or case[0][0] != window['startRva']
            or case[-1][0] + len(bytes.fromhex(case[-1][1])) != window['endRva']):
        _fail('complete-current-case-boundary', window, [case[0], case[-1]])
    route = {'program': case + shared['routeProgram']['program'][11:],
        'codeWindows': [window] + header['callerPrefix']['codeWindows']}
    calls = c['calls']
    if (set(calls) != {'cast', 'child', 'barrier'} or calls['cast'] != shared['nullCastProgram']['program'][0][0]
            or calls['child'] != c['childThunk']['program'][0][0]
            or calls['barrier'] != action['barrierTrampoline']['program'][0][0]):
        _fail('same-current-physical-helpers', 'actual cast, Tick thunk and shared barrier entries', calls)
    null_cast = validate_null_cast_return(image, shared['nullCastProgram'], fail=_fail)
    selected = validate_new_child_union_route(image, route, cast, child, calls, fail=_fail)
    provider = next(r for r in instance['methodContexts'] if r['typeName'] == 'MemoryPack.MemoryPackFormatterProvider')
    contexts = [value['readValueContext'], provider, packable['packableContext']]
    validate_generic_contexts(image, contexts, label=LABEL)
    entries = GenericEntries(image)
    read_context = validate_read_value_context(image, contexts[0], provider, entries, fail=_fail)
    owned = validate_packable_context(image, contexts[2], read_context['readerMethodDefinition'], entries, fail=_fail)
    if child['methodSpec'][:2] != [owned['packableDefinition'], -1]:
        _fail('owned-child-packable-definition', owned['packableDefinition'], child['methodSpec'])
    expected_calls = {k: value['calls'][k] for k in packable['packableCalls']}
    if packable['packableCalls'] != expected_calls:
        _fail('same-shared-packable-physical-calls', expected_calls, packable['packableCalls'])
    transfer = validate_packable_transfer(image, packable['packableProgram'], packable['packableCalls'], fail=_fail)
    closed = validate_packable_thunk(image, c['childThunk'], thunk, packable['packableProgram']['program'][0][0], fail=_fail)
    return {'selectedIndexedUnionPrefix': indexed, 'completeNullCastReturn': null_cast,
        'completeNewChildRoute': selected, 'closedPackableThunk': closed,
        'ownedReadValueContext': read_context, 'ownedPackableContext': owned,
        'completeSharedPackableTransfer': transfer, 'sameConcreteWrapperDefinition': fields['wrapper']['typeDefinition'],
        'sameConcreteWrapperName': wrapper, 'sameConcreteOriginalType': fields['wrapper']['wrappedType'],
        'barrierDisabledCondition': action_summary['unionFalseReturn']['condition'],
        'completeConditionalTickUnionOutputReturnProved': True,
        'runtimeProviderSelectionObserved': False, 'nativeActionCallbackCursorEqualityProved': False}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None):
    c = _contract(); pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated': return {'status': gate.status, 'detail': gate.detail, 'scope': SCOPE, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def matches():
        if not unity.is_file(): return False
        with unity.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest().upper() == pins['UnityPlayer.dll']
    if not matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing', 'detail': 'UnityPlayer.dll missing or mismatched', 'scope': SCOPE, 'nativeInputs': pins}
    try: summary = _validate_image(open_native_image(gate.gameassembly, gate.metadata), c)
    except (ValueError, KeyError, IndexError) as error:
        if isinstance(error, CensusGateError): raise
        _fail('complete-owned-tick-union-route', 'current complete case, typed context, output and normal return', str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched', 'detail': 'native inputs changed during Tick union route proof', 'scope': SCOPE, 'nativeInputs': pins}
    return {'status': 'validated', 'scope': SCOPE, 'nativeInputs': pins, 'summary': summary,
        'childSchemaAdmitted': False, 'positiveListAdmitted': False, 'wholeRootAdmitted': False,
        'runtimeMeaningExact': False, 'reservedMarkerCanonicalAdmission': False, 'evidenceBoundary': c['evidenceBoundary']}
