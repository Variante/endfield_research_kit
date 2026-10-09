"""Current anonymous lookup control; live formatter cache and target stay open."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.dictionary_lookup_control import validate_lookup_control
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _parser_source_snapshots

LABEL = 'buffFormatterDictionaryLookup'
SCHEMA = 'endfield.buff-formatter-dictionary-lookup-native-contract.v1'
SCOPE = 'anonymous-lookup-index-chain-and-disabled-barrier-output-only'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_formatter_dictionary_lookup_native.json'


def _fail(check, expected, actual):
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, scope=SCOPE)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _contract():
    c, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if c.get('scope') != SCOPE or c.get('dependency') != 'buff_formatter_registration_state_native.json':
        _fail('lookup-scope', SCOPE, c.get('scope'))
    return c


def _proof_sources():
    c = _contract()
    return _parser_source_snapshots(Path(__file__)) + [
        _fingerprint(CONTRACT_PATH), _fingerprint(CONTRACTS_DIR / c['dependency']),
        _fingerprint(NATIVE_MAPPER_PATH)]


def _check_caller_pe(pe, dependency, entry_rva):
    proof = dependency['lookupHitProgram']; windows = proof['codeWindows']
    if not proof['program'] or proof['program'][0][0] != dependency['methods']['namedLookup'][3]:
        _fail('actual-caller-entry','named lookup entry owns selected transfer',proof['program'][:1])
    for window in windows:
        raw = pe.bytes_at_va(pe.image_base+window['startRva'],window['endRva']-window['startRva'])
        if hashlib.sha256(raw).hexdigest().upper() != window['sha256'].upper():
            _fail('actual-caller-window','unchanged independently reviewed caller bytes',window['startRva'])
    matching = []
    for rva,raw_hex,*_ in proof['program']:
        raw = bytes.fromhex(raw_hex)
        if not any(w['startRva'] <= rva < rva+len(raw) <= w['endRva'] for w in windows):
            _fail('actual-caller-instruction-ownership','instruction inside caller window',rva)
        if pe.bytes_at_va(pe.image_base+rva,len(raw)) != raw:
            _fail('actual-caller-instruction','current original caller bytes',rva)
        if len(raw)==5 and raw[0]==0xe8 and rva+5+int.from_bytes(raw[1:],'little',signed=True)==entry_rva:
            matching.append(rva)
    if len(matching) != 1:
        _fail('actual-caller-call-target','one actual selected E8 call to current lookup body',matching)


def _validate_selected(gameassembly, c):
    dependency, _ = read_reviewed_contract(CONTRACTS_DIR / c['dependency'],
        schema='endfield.buff-formatter-registration-state-native-contract.v1',
        status='exact-current-build',label=LABEL)
    if dependency['nativeInputs'] != c['nativeInputs']:
        _fail('dependency-build', c['nativeInputs'],dependency['nativeInputs'])
    if dependency['calls']['dictionaryLookup'] != c['entryRva']:
        _fail('actual-caller-target',dependency['calls']['dictionaryLookup'],c['entryRva'])
    mapper = load_native_mapper(NATIVE_MAPPER_PATH)
    pe = mapper.PeImage(Path(gameassembly))
    _check_caller_pe(pe,dependency,c['entryRva'])
    # These public BodyIndex ownership properties use only PE/.pdata; no
    # metadata or generic declaration is inferred by this byte-only adapter.
    index = BodyIndex(SimpleNamespace(mapper=mapper, pe=pe, metadata=None))
    return {**validate_lookup_control(index,c),'independentNamedLookupCallerBytesAndActualTargetJoined':True}


def validate_current_native_contract(*, gameassembly=None, metadata=None):
    c = _contract(); pins = c['nativeInputs']; sources = _proof_sources()
    gate = check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
                                        gameassembly=gameassembly,metadata=metadata)
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
        summary = _validate_selected(gate.gameassembly,c)
    except (ValueError,KeyError,IndexError,TypeError,OverflowError) as error:
        if isinstance(error,CensusGateError): raise
        _fail('native-lookup-control','complete owned grammar, original branches, slot/index/output/frame joins',str(error))
    after = check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    current = unity_hash()
    if after.status != 'validated' or current != pins['UnityPlayer.dll']:
        return {**result,'status':after.status if after.status != 'validated' else 'missing' if current is None else 'mismatched',
                'detail':'native inputs changed during lookup control validation'}
    drift = [row['path'] for row in sources if _fingerprint(Path(row['path'])) != row]
    if drift: _fail('proof-source-drift','unchanged source/contract closure',drift)
    return {**result,'status':'validated','summary':summary}
