"""Authenticate provider arguments and selected lookup return; cache state open."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.formatter_registration_state import validate_registration_state_transfers
from scripts.game_data.memorypack.formatter_provider_sources import validate_provider_transfer
from scripts.game_data.memorypack import buff_action_array_callback_binding as binding
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _parser_source_snapshots

LABEL = 'buffFormatterRegistrationState'
SCHEMA = 'endfield.buff-formatter-registration-state-native-contract.v1'
SCOPE = 'provider-registration-arguments-and-selected-lookup-hit-return-only'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_formatter_registration_state_native.json'


def _fail(check, expected, actual):
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, scope=SCOPE)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract():
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (c.get('scope') != SCOPE or set(c.get('dependencies', {})) != {'header','provider'}
            or set(c.get('methods',{})) != {'registerWrap','publicLookup','namedLookup'}
            or set(c.get('usages',{})) != {'providerClass','setter','lookup'}
            or set(c.get('classCarrierOffsets',{})) != {'staticStorage','initialized'}):
        _fail('registration-state-scope', 'two dependencies, three methods/usages and selected carrier members', c.get('scope'))
    return c


def _proof_sources():
    rows = binding._proof_sources() + _parser_source_snapshots(Path(__file__)) + [_fingerprint(CONTRACT_PATH)]
    return sorted({row['path']:row for row in rows}.values(), key=lambda row:row['path'])


def _validate_image(image, c):
    h, _ = read_reviewed_contract(CONTRACTS_DIR / c['dependencies']['header'],
        schema='endfield.buff-action-union-header-native-contract.v1', status='exact-current-build', label=LABEL)
    p, _ = read_reviewed_contract(CONTRACTS_DIR / c['dependencies']['provider'],
        schema='endfield.buff-formatter-provider-native-contract.v1', status='exact-current-build', label=LABEL)
    if h['nativeInputs'] != c['nativeInputs'] or p['nativeInputs'] != c['nativeInputs']:
        _fail('dependency-build', c['nativeInputs'], [h['nativeInputs'],p['nativeInputs']])
    eager = h['adapterRegistrationFlow']
    if (eager['helperMethods']['registerWrap'] != c['methods']['registerWrap']
            or eager['actualCalls']['registerWrap'] != c['methods']['registerWrap'][3]
            or p['calls']['formatterResult'] != c['calls']['formatterResult']):
        _fail('actual-eager-and-array-result-helper-join', 'independently owned actual caller targets', [eager['helperMethods'],p['calls']])
    validate_eager_wrap_registration(image, eager, label=LABEL)
    provider = validate_provider_transfer(image, p['proof'], p['calls'], fail=_fail)
    summary = validate_registration_state_transfers(image, c)
    return {**summary, 'originalEagerRegistrationCallerJoined':True,
        'originalType':eager['originalType'],'wrapperType':eager['wrapperType'],
        'physicalArrayProviderReturn':provider,'physicalArrayProviderNamedIdentityProved':False,
        'physicalResultHelperWholeControlProved':False}


def validate_current_native_contract(*, gameassembly=None, metadata=None):
    c = _contract(); pins = c['nativeInputs']; sources = _proof_sources()
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    result = {'status':gate.status,'scope':SCOPE,'nativeInputs':pins,'provenance':{'inputs':sources},
        'evidenceBoundary':c['evidenceBoundary'],'runtimeRegistrationStateJoined':False,
        'actualArrayCallbackTargetProved':False,'callbackCursorEqualityProved':False,
        'positiveListAdmitted':False,'wholeRootAdmitted':False,'runtimeMeaningExact':False}
    if gate.status != 'validated': return {**result,'detail':gate.detail}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_hash():
        if not unity.is_file(): return None
        with unity.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest().upper()
    current = unity_hash()
    if current != pins['UnityPlayer.dll']:
        return {**result,'status':'missing' if current is None else 'mismatched','detail':'UnityPlayer.dll missing or mismatched'}
    try:
        summary = _validate_image(open_native_image(gate.gameassembly,gate.metadata),c)
    except (ValueError,KeyError,IndexError,TypeError,OverflowError) as error:
        if isinstance(error,CensusGateError): raise
        _fail('native-registration-transfer', 'complete original caller/storage/context/output joins',str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    current = unity_hash()
    if after.status != 'validated' or current != pins['UnityPlayer.dll']:
        return {**result,'status':after.status if after.status != 'validated' else 'missing' if current is None else 'mismatched',
            'detail':'native inputs changed during registration transfer validation'}
    drift = [row['path'] for row in sources if _fingerprint(Path(row['path'])) != row]
    if drift: _fail('proof-source-drift','unchanged source/contract closure',drift)
    return {**result,'status':'validated','summary':summary}
