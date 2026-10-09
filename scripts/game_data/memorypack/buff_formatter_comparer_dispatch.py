"""Authenticate actual lookup-to-dispatch transfers; live target meaning open."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.comparer_dispatch_control import validate_comparer_dispatch_control
from scripts.game_data.il2cpp.dictionary_lookup_control import validate_lookup_control
from scripts.game_data.il2cpp.integer_widths import decode_width_aware_integer_instructions
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH,read_reviewed_contract
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError,_fingerprint,_parser_source_snapshots

LABEL='buffFormatterComparerDispatch'
SCHEMA='endfield.buff-formatter-comparer-dispatch-native-contract.v1'
SCOPE='anonymous-record-selector-and-comparer-dispatch-control-only'
CONTRACT_PATH=CONTRACTS_DIR/'buff_formatter_comparer_dispatch_native.json'


def _fail(check,expected,actual):
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,scope=SCOPE);error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error


def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if c.get('scope')!=SCOPE or c.get('dependency')!='buff_formatter_dictionary_lookup_native.json':
        _fail('scope',SCOPE,c.get('scope'))
    return c


def _proof_sources():
    c=_contract()
    return _parser_source_snapshots(Path(__file__))+[_fingerprint(CONTRACT_PATH),
        _fingerprint(CONTRACTS_DIR/c['dependency']),_fingerprint(NATIVE_MAPPER_PATH)]


def _check_lookup_transfers(index,parent,c):
    pe=index.pe;mapper=index.mapper
    for role,window in c['callerTransfers'].items():
        start=window['startRva'];end=window['endRva']
        if not any(w['startRva']<=start<end<=w['endRva'] for w in parent['codeWindows']):
            _fail('caller-transfer-ownership','inside complete validated parent',window)
        rows=decode_width_aware_integer_instructions(mapper,pe.bytes_at_va(pe.image_base+start,end-start),pe.image_base+start)
        g=ProgramGrammar(rows,label=LABEL+'.'+role)
        if role=='keyWordProducer': g.take('mov ecx, 0x1','mov r9, r12','mov r8, rsi','mov rdx, rax')
        else: g.take('xor ecx, ecx','mov [rsp+0x20], r12','mov r9, rbp','mov r8, rsi','mov rdx, rax')
        g.call(pe.image_base+c['programs'][role]['entryRva']);g.finish()


def _validate_selected(gameassembly,c):
    parent,_=read_reviewed_contract(CONTRACTS_DIR/c['dependency'],
        schema='endfield.buff-formatter-dictionary-lookup-native-contract.v1',status='exact-current-build',label=LABEL)
    if parent['nativeInputs']!=c['nativeInputs']: _fail('dependency-build',c['nativeInputs'],parent['nativeInputs'])
    for role,program in c['programs'].items():
        if parent['calls'][role]!=program['entryRva']: _fail('actual-helper-target',parent['calls'][role],program['entryRva'])
    mapper=load_native_mapper(NATIVE_MAPPER_PATH);pe=mapper.PeImage(Path(gameassembly))
    index=BodyIndex(SimpleNamespace(mapper=mapper,pe=pe,metadata=None))
    validate_lookup_control(index,parent);_check_lookup_transfers(index,parent,c)
    return {**validate_comparer_dispatch_control(index,c),'completeParentLookupAndActualSelectorTransfersJoined':True,
            'lookupSelectors':{'keyWordProducer':1,'candidatePredicate':0}}


def validate_current_native_contract(*,gameassembly=None,metadata=None):
    c=_contract();pins=c['nativeInputs'];sources=_proof_sources()
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    result={'status':gate.status,'scope':SCOPE,'nativeInputs':pins,'provenance':{'inputs':sources},
        'evidenceBoundary':c['evidenceBoundary'],'wordHashAndPredicateEqualityMeaningProved':False,
        'actualRuntimeTargetSelected':False,'actualArrayCallbackTargetProved':False,
        'callbackCursorEqualityProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False}
    if gate.status!='validated': return {**result,'detail':gate.detail}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_hash():
        if not unity.is_file(): return None
        with unity.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest().upper()
    current=unity_hash()
    if current!=pins['UnityPlayer.dll']:
        return {**result,'status':'missing' if current is None else 'mismatched','detail':'UnityPlayer.dll missing or mismatched'}
    try: summary=_validate_selected(gate.gameassembly,c)
    except (ValueError,KeyError,IndexError,TypeError,OverflowError) as error:
        if isinstance(error,CensusGateError): raise
        _fail('native-dispatch-control','complete owned widths, selectors, branches, pair, arguments and return',str(error))
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    current=unity_hash()
    if after.status!='validated' or current!=pins['UnityPlayer.dll']:
        return {**result,'status':after.status if after.status!='validated' else 'missing' if current is None else 'mismatched',
                'detail':'native inputs changed during dispatch validation'}
    drift=[r['path'] for r in sources if _fingerprint(Path(r['path']))!=r]
    if drift: _fail('proof-source-drift','unchanged source/contract closure',drift)
    return {**result,'status':'validated','summary':summary}
